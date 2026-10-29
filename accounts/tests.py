from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from community.models import Post, PostLike, Comment as CommunityComment


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

        first = Post.objects.create(
            author=self.user, caption='First hike'
        )
        second = Post.objects.create(
            author=self.user, caption='Second hike'
        )
        unliked = Post.objects.create(
            author=self.user, caption='Third hike'
        )
        outside = Post.objects.create(
            author=other, caption='Other hike'
        )

        PostLike.objects.create(post=first, user=self.user)
        PostLike.objects.create(post=first, user=other)
        PostLike.objects.create(post=second, user=other)
        PostLike.objects.create(post=outside, user=self.user)

        self.client.force_login(self.user)
        response = self.client.get(reverse('accounts:account_detail'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_likes'], 3)
        self.assertEqual(response.context['moments_count'], 3)

        counts = {
            post.pk: post.likes_count
            for post in response.context['moments']
        }
        self.assertEqual(counts, {
            first.pk: 2,
            second.pk: 1,
            unliked.pk: 0,
        })

        self.assertContains(response, '2 likes')



class MergedAccountFixTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='merge-hiker', email='hiker@example.com', password='OriginalPass!392')
        self.client.force_login(self.user)

    def test_delete_confirmation_and_wrong_password(self):
        url = reverse('accounts:delete_account')
        self.assertEqual(self.client.get(url).status_code, 200)
        response = self.client.post(url, {'password': 'wrong'})
        self.assertContains(response, 'Incorrect password')
        self.assertTrue(get_user_model().objects.filter(pk=self.user.pk).exists())

    def test_moment_like_and_unlike(self):
        post = Post.objects.create(
            author=self.user,
            caption='Trail'
        )
        url = reverse('accounts:toggle_like', args=[post.pk])

        self.assertEqual(self.client.get(url).status_code, 405)

        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            'liked': True,
            'total_likes': 1
        })

        response = self.client.get(reverse('accounts:account_detail'))
        self.assertEqual(response.context['total_likes'], 1)

        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            'liked': False,
            'total_likes': 0
        })

    def test_add_comment_and_reject_empty_comment(self):
        post = Post.objects.create(
            author=self.user,
            caption='Trail'
        )
        url = reverse('accounts:add_comment', args=[post.pk])

        self.assertEqual(self.client.get(url).status_code, 405)

        response = self.client.post(url, {'text': '  '})
        self.assertEqual(response.status_code, 400)

        response = self.client.post(url, {'text': 'Great hike'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['total_comments'], 1)

        self.assertEqual(
            CommunityComment.objects.get(post=post).text,
            'Great hike'
        )

    def test_edit_rejects_duplicate_email(self):
        from .forms import EditAccountForm
        get_user_model().objects.create_user(username='other', email='other@example.com')
        form = EditAccountForm(instance=self.user, data={'full_name': 'Hiker',
            'username': self.user.username, 'email': 'OTHER@example.com'})
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_edit_shows_duplicate_username_error(self):
        get_user_model().objects.create_user(username='taken')
        response = self.client.post(reverse('accounts:edit_account'), {
            'full_name': 'Hiker', 'username': 'taken', 'email': self.user.email}, follow=True)
        self.assertContains(response, 'A user with that username already exists.')

    def test_single_word_name_clears_last_name(self):
        self.user.last_name = 'Tester'
        self.user.save()
        self.client.post(reverse('accounts:edit_account'), {
            'full_name': 'Solo', 'username': self.user.username, 'email': self.user.email})
        self.user.refresh_from_db()
        self.assertEqual((self.user.first_name, self.user.last_name), ('Solo', ''))

    def test_anonymous_edit_redirects_to_login(self):
        self.client.logout()
        response = self.client.post(reverse('accounts:edit_account'), {})
        self.assertEqual(response.status_code, 302)

    def test_password_reset_end_to_end(self):
        from django.core import mail
        from django.test import override_settings
        import re
        self.client.logout()
        with override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'):
            response = self.client.post(reverse('accounts:password_reset'), {'email': self.user.email}, follow=True)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(mail.outbox), 1)
            path = re.search(r'http://testserver([^"\s]+)', mail.outbox[0].body).group(1)
            response = self.client.get(path, follow=True)
            self.assertEqual(response.status_code, 200)
            response = self.client.post(response.request['PATH_INFO'], {
                'new_password1': 'ChangedPassword!729', 'new_password2': 'ChangedPassword!729'}, follow=True)
            self.assertEqual(response.status_code, 200)
            self.user.refresh_from_db()
            self.assertTrue(self.user.check_password('ChangedPassword!729'))
            self.assertTemplateUsed(response, 'registration/password_reset_complete.html')
