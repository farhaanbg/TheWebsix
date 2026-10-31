from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Question

User = get_user_model()


class QuestionAndAnswerTests(TestCase):
    def setUp(self):
        self.hiker = User.objects.create_user('hiker', password='pass12345')
        self.other = User.objects.create_user('other', password='pass12345')
        self.admin = User.objects.create_superuser('boss', password='pass12345')
        self.question = Question.objects.create(
            author=self.other, title='Is Le Pouce suitable for beginners?',
            category=Question.Category.HIKES)

    def ask(self, title='Do I need hiking boots for this trail?', **extra):
        data = {'title': title, 'category': 'equipment', 'details': '', **extra}
        return self.client.post(reverse('qa:ask'), data)

    def test_visitor_can_read_qa_page(self):
        response = self.client.get(reverse('qa:list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Is Le Pouce suitable for beginners?')
        self.assertContains(response, 'Log in')          # no form for visitors

    def test_visitor_cannot_ask(self):
        response = self.ask()
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('accounts:login'), response['Location'])
        self.assertEqual(Question.objects.count(), 1)

    def test_logged_in_user_can_ask_and_is_set_as_author(self):
        self.client.login(username='hiker', password='pass12345')
        response = self.ask(author=self.other.pk)        # trying to fake the author
        self.assertEqual(response.status_code, 302)
        question = Question.objects.get(author=self.hiker)
        self.assertEqual(question.title, 'Do I need hiking boots for this trail?')

    def test_question_mark_added_and_short_question_rejected(self):
        self.client.login(username='hiker', password='pass12345')
        self.ask(title='What time do hikes usually start')
        self.assertTrue(Question.objects.filter(title='What time do hikes usually start?').exists())
        response = self.ask(title='Hi?')
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, 'at least 10 characters', status_code=400)

    def test_duplicate_question_rejected(self):
        self.client.login(username='hiker', password='pass12345')
        self.ask()
        response = self.ask(title='do i need hiking boots for this trail?')
        self.assertContains(response, 'already asked', status_code=400)
        self.assertEqual(Question.objects.filter(author=self.hiker).count(), 1)

    def test_invalid_category_rejected(self):
        self.client.login(username='hiker', password='pass12345')
        response = self.ask(category='hacking')
        self.assertEqual(response.status_code, 400)

    def test_user_can_delete_own_question_only(self):
        self.client.login(username='hiker', password='pass12345')
        response = self.client.post(reverse('qa:delete', args=[self.question.pk]))
        self.assertEqual(response.status_code, 404)        # not theirs
        self.assertTrue(Question.objects.filter(pk=self.question.pk).exists())
        self.client.logout()
        self.client.login(username='other', password='pass12345')
        self.client.post(reverse('qa:delete', args=[self.question.pk]))
        self.assertFalse(Question.objects.filter(pk=self.question.pk).exists())

    def test_hidden_questions_not_shown(self):
        self.question.is_visible = False
        self.question.save()
        response = self.client.get(reverse('qa:list'))
        self.assertNotContains(response, 'Is Le Pouce suitable for beginners?')

    def test_answer_sets_timestamp_and_shows_on_page(self):
        self.question.answer = 'Yes, it is our easiest hike.'
        self.question.answered_by = self.admin
        self.question.save()
        self.assertIsNotNone(self.question.answered_at)
        response = self.client.get(reverse('qa:list') + '?show=answered')
        self.assertContains(response, 'our easiest hike')

    def test_admin_answer_records_who_answered(self):
        self.client.login(username='boss', password='pass12345')
        url = reverse('admin:qa_question_change', args=[self.question.pk])
        response = self.client.post(url, {
            'title': self.question.title, 'category': 'hikes', 'details': '',
            'answer': 'Yes, bring water.', 'is_visible': 'on',
        })
        self.assertEqual(response.status_code, 302)
        self.question.refresh_from_db()
        self.assertEqual(self.question.answered_by, self.admin)

    def test_search_and_filter(self):
        Question.objects.create(author=self.hiker, title='Can I pay by card on the day?',
                                category=Question.Category.BOOKINGS)
        response = self.client.get(reverse('qa:list'), {'q': 'card'})
        self.assertContains(response, 'pay by card')
        self.assertNotContains(response, 'Le Pouce')
        response = self.client.get(reverse('qa:list'), {'category': 'hikes'})
        self.assertContains(response, 'Le Pouce')
        self.assertNotContains(response, 'pay by card')

    def test_str(self):
        self.assertEqual(str(self.question), 'Is Le Pouce suitable for beginners?')
