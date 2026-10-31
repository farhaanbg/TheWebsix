from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from .models import Post, Review


class ReviewManagementTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(username='review-owner')
        self.other = get_user_model().objects.create_user(username='review-other')
        self.review = Review.objects.create(
            author=self.owner, name='Owner', rating=4, text='Lovely trail')
        self.edit_url = reverse('community:review_edit', args=[self.review.pk])
        self.delete_url = reverse('community:review_delete', args=[self.review.pk])
        self.client.force_login(self.owner)

    def test_owner_can_edit_review_and_invalid_rating_is_rejected(self):
        response = self.client.get(self.edit_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['form'].initial['text'], 'Lovely trail')
        response = self.client.post(self.edit_url, {
            'name': 'Updated owner', 'rating': 5, 'text': 'Excellent trail',
        })
        self.assertRedirects(response, reverse('community:reviews'))
        self.review.refresh_from_db()
        self.assertEqual((self.review.rating, self.review.text), (5, 'Excellent trail'))
        response = self.client.post(self.edit_url, {
            'name': 'Owner', 'rating': 6, 'text': 'Invalid',
        })
        self.assertTrue(response.context['form'].errors)
        self.review.refresh_from_db()
        self.assertEqual(self.review.rating, 5)

    def test_delete_confirmation_preserves_review_until_post(self):
        self.assertEqual(self.client.get(self.delete_url).status_code, 200)
        self.assertTrue(Review.objects.filter(pk=self.review.pk).exists())
        self.assertRedirects(self.client.post(self.delete_url), reverse('community:reviews'))
        self.assertFalse(Review.objects.filter(pk=self.review.pk).exists())

    def test_other_user_cannot_edit_or_delete(self):
        self.client.force_login(self.other)
        for url in (self.edit_url, self.delete_url):
            self.assertEqual(self.client.get(url).status_code, 403)
            self.assertEqual(self.client.post(url, {}).status_code, 403)
        self.assertTrue(Review.objects.filter(pk=self.review.pk).exists())

    def test_staff_can_manage_reviews(self):
        self.other.is_staff = True
        self.other.save()
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.edit_url).status_code, 200)
        self.assertRedirects(self.client.post(self.delete_url), reverse('community:reviews'))

    def test_guest_is_sent_to_login(self):
        self.client.logout()
        for url in (self.edit_url, self.delete_url):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)
            self.assertIn(reverse('accounts:login'), response['Location'])


class CommunityLoginRedirectTests(TestCase):
    def test_old_login_address_reaches_accounts_login(self):
        for debug in (True, False):
            with self.subTest(debug=debug), override_settings(DEBUG=debug):
                self.assertRedirects(
                    self.client.get(reverse('community:login')),
                    reverse('accounts:login'),
                )

    def test_return_destination_is_preserved(self):
        from urllib.parse import urlencode

        query = urlencode({'next': reverse('community:post_create')})
        self.assertRedirects(
            self.client.get(reverse('community:login') + '?' + query),
            reverse('accounts:login') + '?' + query,
        )

    def test_signed_in_user_reaches_dashboard(self):
        user = get_user_model().objects.create_user(username='legacy-login-hiker')
        self.client.force_login(user)
        response = self.client.get(reverse('community:login'), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.request['PATH_INFO'], reverse('accounts:account_detail'))


class MergedCommunityFixTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='community-hiker')
        self.post = Post.objects.create(author=self.user, caption='A lovely trail')
        self.client.force_login(self.user)

    def test_comment_page_and_invalid_submission_render(self):
        url = reverse('community:comment_create', args=[self.post.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(self.client.post(url, {'text': ''}).status_code, 200)
        response = self.client.post(url, {'text': 'Great hike', 'next': 'community'})
        self.assertRedirects(response, reverse('community:community'))
        self.assertEqual(self.post.comments.get().text, 'Great hike')

    def test_delete_confirmation_and_submission(self):
        url = reverse('community:post_delete', args=[self.post.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertRedirects(self.client.post(url), reverse('community:community'))
        self.assertFalse(Post.objects.filter(pk=self.post.pk).exists())

    def test_delete_rejects_other_user(self):
        other = get_user_model().objects.create_user(username='other')
        self.client.force_login(other)
        url = reverse('community:post_delete', args=[self.post.pk])
        self.assertEqual(self.client.post(url).status_code, 403)
        self.assertTrue(Post.objects.filter(pk=self.post.pk).exists())

    def test_profile_link_and_comment_script(self):
        response = self.client.get(reverse('community:community'))
        self.assertContains(response, 'href="' + reverse('accounts:account_detail') + '"')
        self.assertContains(response, 'js/community.js')
        self.assertContains(response, 'data-comment-toggle')
        response = self.client.get(reverse('community:reviews'))
        self.assertContains(response, 'href="' + reverse('accounts:account_detail') + '"')

    def test_like_returns_to_details(self):
        response = self.client.post(reverse('community:post_like', args=[self.post.pk]),
            {'liked': '1', 'next': 'detail'})
        self.assertRedirects(response, self.post.get_absolute_url())
        self.assertEqual(self.post.likes.count(), 1)

    def test_review_creation_date_is_rendered(self):
        review = Review.objects.create(author=self.user, name='Hiker', rating=4, text='Lovely')
        from django.utils import timezone
        self.assertContains(self.client.get(reverse('community:reviews')),
            timezone.localtime(review.created_at).strftime('%d/%m/%Y'))
