from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from .models import Moment


class AccountDashboardTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='hiker', password='test-password')

    def test_login_redirects_to_working_empty_dashboard(self):
        response = self.client.post(reverse('accounts:login'), {
            'username': 'hiker', 'password': 'test-password',
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_likes'], 0)
        self.assertEqual(response.context['moments_count'], 0)

    def test_dashboard_counts_likes_on_own_moments(self):
        other = get_user_model().objects.create_user(username='other-hiker')
        first = Moment.objects.create(user=self.user, title='First hike', image='moments/test.jpg')
        second = Moment.objects.create(user=self.user, title='Second hike', image='moments/test.jpg')
        unliked = Moment.objects.create(user=self.user, title='Third hike', image='moments/test.jpg')
        outside = Moment.objects.create(user=other, title='Other hike', image='moments/test.jpg')
        first.likes.add(self.user, other)
        second.likes.add(other)
        outside.likes.add(self.user)
        self.client.force_login(self.user)
        response = self.client.get(reverse('accounts:account_detail'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_likes'], 3)
        self.assertEqual(response.context['moments_count'], 3)
        counts = {moment.pk: moment.likes_count for moment in response.context['moments']}
        self.assertEqual(counts, {first.pk: 2, second.pk: 1, unliked.pk: 0})
        self.assertContains(response, '2 likes')
