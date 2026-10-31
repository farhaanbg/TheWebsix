from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from community.models import Post, PostLike, Comment as CommunityComment


class LoginReturnDestinationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='return-hiker', password='ReturnPass!392')

    def test_login_resumes_local_destination(self):
        destination = reverse('qa:list') + '?show=unanswered'
        response = self.client.post(reverse('accounts:login'), {
            'username': self.user.username, 'password': 'ReturnPass!392',
            'next': destination,
        })
        self.assertRedirects(response, destination)
        self.assertIn('no-store', response['Cache-Control'])

    def test_external_destinations_fall_back_to_dashboard(self):
        for destination in ('https://example.org/', '//example.org/'):
            with self.subTest(destination=destination):
                self.client.logout()
                response = self.client.post(reverse('accounts:login'), {
                    'username': self.user.username, 'password': 'ReturnPass!392',
                    'next': destination,
                })
                self.assertRedirects(response, reverse('accounts:account_detail'))

    def test_signed_in_user_resumes_local_destination(self):
        self.client.force_login(self.user)
        self.assertRedirects(self.client.get(reverse('accounts:login'), {
            'next': reverse('qa:list'),
        }), reverse('qa:list'))

    def test_failed_login_retains_destination(self):
        response = self.client.post(reverse('accounts:login'), {
            'username': self.user.username, 'password': 'wrong',
            'next': reverse('qa:list'),
        })
        self.assertEqual(response.context['next'], reverse('qa:list'))
        self.assertContains(response, 'name="next"')


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

    def test_signup_rejects_duplicate_email(self):
        from .forms import SignupForm
        form = SignupForm(data={
            'full_name': 'New Hiker', 'username': 'new-hiker',
            'email': 'HIKER@example.com',
            'password1': 'NewPassword!924', 'password2': 'NewPassword!924',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_duplicate_email_login_does_not_crash_and_username_still_works(self):
        get_user_model().objects.create_user(
            username='duplicate', email=self.user.email, password='OtherPass!392')
        self.client.logout()
        response = self.client.post(reverse('accounts:login'), {
            'username': self.user.email, 'password': 'OriginalPass!392',
        })
        self.assertContains(response, 'Invalid username/email or password.')
        self.assertNotIn('_auth_user_id', self.client.session)
        response = self.client.post(reverse('accounts:login'), {
            'username': self.user.username, 'password': 'OriginalPass!392',
        })
        self.assertRedirects(response, reverse('accounts:account_detail'))

    def test_dashboard_shares_navigation_and_supports_posts_without_photos(self):
        Post.objects.create(author=self.user, caption='A text-only trail update')
        response = self.client.get(reverse('accounts:account_detail'))
        self.assertContains(response, 'A text-only trail update')
        self.assertContains(response, 'No image available')
        self.assertContains(response, 'href="/"')
        self.assertContains(response, 'href="/hikes/"')
        self.assertContains(response, reverse('community:post_create'))
        self.assertContains(response, '<title>', count=1)

    def test_account_comments_use_community_records_and_consistent_local_times(self):
        from django.utils import timezone
        post = Post.objects.create(author=self.user, caption='Trail')
        url = reverse('accounts:add_comment', args=[post.pk])
        response = self.client.post(url, {'text': '<strong>Great hike</strong>'})
        comment = CommunityComment.objects.get(post=post)
        expected_time = timezone.localtime(comment.created_at).strftime('%b %d, %Y %H:%M')
        self.assertEqual(response.json()['comment']['created_at'], expected_time)
        listing = self.client.get(reverse('accounts:get_comments', args=[post.pk]))
        self.assertEqual(listing.json()['comments'][0]['created_at'], expected_time)
        self.assertEqual(listing.json()['comments'][0]['text'], '<strong>Great hike</strong>')
        detail = self.client.get(post.get_absolute_url())
        self.assertContains(detail, '&lt;strong&gt;Great hike&lt;/strong&gt;')

    def test_account_delete_actions_enforce_community_record_ownership(self):
        other = get_user_model().objects.create_user(username='unrelated-hiker')
        post = Post.objects.create(author=other, caption='Their trail')
        comment = CommunityComment.objects.create(post=post, author=other, text='Their comment')
        self.assertEqual(self.client.post(
            reverse('accounts:delete_moment', args=[post.pk])).status_code, 404)
        url = reverse('accounts:delete_comment', args=[comment.pk])
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(self.client.post(url).status_code, 403)
        self.assertTrue(CommunityComment.objects.filter(pk=comment.pk).exists())
        self.client.force_login(other)
        response = self.client.post(url)
        self.assertEqual(response.json()['total_comments'], 0)
        self.assertRedirects(self.client.post(
            reverse('accounts:delete_moment', args=[post.pk])),
            reverse('accounts:account_detail'))
        self.assertFalse(Post.objects.filter(pk=post.pk).exists())

    def test_shared_post_creation_rejects_non_image_uploads(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        response = self.client.post(reverse('community:post_create'), {
            'caption': 'Trail',
            'image': SimpleUploadedFile('fake.jpg', b'not an image', content_type='image/jpeg'),
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('image', response.context['form'].errors)
        self.assertFalse(Post.objects.filter(author=self.user).exists())

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
