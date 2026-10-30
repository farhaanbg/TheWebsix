from datetime import time, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from bookings.models import Booking, BookingNotification
from .forms import HikeAdminForm
from .models import Announcement, Guide, Hike, HikeChange, SavedHike
from .testing import published_hike


class HikeRequirementsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username='requirements-hiker')
        cls.other = get_user_model().objects.create_user(username='other-requirements-hiker')
        cls.staff = get_user_model().objects.create_superuser(username='hike-manager')
        cls.fields = dict(location='Chamarel', district='Black River',
                          date=timezone.localdate() + timedelta(days=7), difficulty='easy',
                          price=100, distance_km=5, duration_minutes=90, capacity=10)
        cls.hike = published_hike(title='Upcoming waterfall', **cls.fields)

    def reservation(self, **kwargs):
        fields = dict(user=self.user, hike=self.hike, customer_name='Hiker', spots=2,
                      payment_method='cash')
        fields.update(kwargs)
        return Booking.objects.create(**fields)

    def test_cancellation_retains_public_hike_and_cancels_only_active_bookings(self):
        active = self.reservation()
        inactive = self.reservation(user=self.other)
        inactive.cancel()
        self.hike.cancel('Unsafe weather', actor=self.staff)
        self.hike.cancel('Unsafe weather', actor=self.staff)
        active.refresh_from_db()
        self.hike.refresh_from_db()
        self.assertEqual(active.status, Booking.Status.CANCELLED)
        self.assertEqual(self.hike.reserved_spots, 0)
        self.assertEqual(HikeChange.objects.count(), 1)
        self.assertEqual(BookingNotification.objects.count(), 1)
        self.assertEqual(BookingNotification.objects.get().user_id, self.user.pk)
        response = self.client.get(self.hike.get_absolute_url())
        self.assertContains(response, 'Cancelled')
        self.assertContains(response, 'Unsafe weather')
        self.assertNotContains(response, 'Book this hike')
        self.assertContains(self.client.get(reverse('hikes:list')), self.hike.title)
        self.client.force_login(self.user)
        self.assertRedirects(self.client.get(reverse('bookings:book_hike', args=[self.hike.pk])),
                             self.hike.get_absolute_url())
        with self.assertRaises(ValidationError):
            self.reservation()

    def test_postponement_keeps_reservations_and_notifies_owners_privately(self):
        booking = self.reservation()
        date = self.hike.date + timedelta(days=2)
        self.hike.postpone(date, time(9), 'Trail maintenance', actor=self.staff)
        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.PENDING)
        self.assertEqual(self.hike.reserved_spots, 2)
        self.assertEqual(self.hike.status, Hike.Status.POSTPONED)
        event = self.hike.changes.get()
        self.assertEqual(event.new_date, date)
        self.assertEqual(event.changed_by_id, self.staff.pk)
        self.client.force_login(self.user)
        response = self.client.get(reverse('bookings:my_bookings'))
        self.assertContains(response, 'has been rescheduled')
        self.assertContains(response, 'Trail maintenance')
        self.client.force_login(self.other)
        self.assertNotContains(self.client.get(reverse('bookings:my_bookings')), 'Trail maintenance')

    def test_plain_schedule_edits_also_record_history(self):
        self.reservation()
        self.hike.departure_time = time(10)
        self.hike.save(update_fields=['departure_time'])
        self.assertEqual(self.hike.status, Hike.Status.POSTPONED)
        self.assertEqual(BookingNotification.objects.count(), 1)
        self.hike.title = 'A new title'
        self.hike.save(update_fields=['title'])
        self.assertEqual(HikeChange.objects.count(), 1)

    def test_failed_notification_rolls_back_hike_and_booking_cancellation(self):
        booking = self.reservation()
        with patch('bookings.models.BookingNotification.objects.using') as manager:
            manager.return_value.create.side_effect = RuntimeError('notification failed')
            with self.assertRaises(RuntimeError):
                self.hike.cancel()
        self.hike.refresh_from_db()
        booking.refresh_from_db()
        self.assertEqual(self.hike.status, Hike.Status.SCHEDULED)
        self.assertEqual(booking.status, Booking.Status.PENDING)
        self.assertEqual(self.hike.reserved_spots, 2)
        self.assertFalse(HikeChange.objects.exists())

    def test_postponement_requires_changed_future_schedule(self):
        with self.assertRaises(ValidationError):
            self.hike.postpone(self.hike.date, self.hike.departure_time)
        with self.assertRaises(ValidationError):
            self.hike.postpone(timezone.localdate() - timedelta(days=1), time(9))

    def test_upcoming_scope_statistics_and_choices_exclude_past_and_drafts(self):
        published_hike(title='Past trail', **{**self.fields, 'date': timezone.localdate() - timedelta(days=1),
                                           'location': 'Old location'})
        Hike.objects.create(title='Unpublished draft', **self.fields)
        response = self.client.get(reverse('hikes:list'))
        self.assertContains(response, self.hike.title)
        self.assertNotContains(response, 'Past trail')
        self.assertNotContains(response, 'Unpublished draft')
        self.assertEqual(response.context['available_count'], 1)
        self.assertEqual(response.context['guide_count'], 1)
        self.assertNotIn(('Old location', 'Old location'), response.context['form'].fields['location'].choices)
        response = self.client.get(reverse('hikes:list'), {'scope': 'all'})
        self.assertContains(response, 'Past trail')
        self.assertNotContains(response, 'Unpublished draft')

    def test_same_day_departures_are_consistent_with_directory(self):
        now = timezone.localtime().replace(hour=12, minute=0, second=0, microsecond=0)
        published_hike(title='Morning trail', **{**self.fields, 'date': now.date(), 'departure_time': time(10)})
        published_hike(title='Afternoon trail', **{**self.fields, 'date': now.date(), 'departure_time': time(14)})
        with patch('hikes.models.timezone.localtime', return_value=now):
            response = self.client.get(reverse('hikes:list'))
        self.assertNotContains(response, 'Morning trail')
        self.assertContains(response, 'Afternoon trail')

    def test_multiple_guide_details_are_visible_and_counted_once(self):
        guide = Guide.objects.create(name='Second guide', biography='Experienced local guide')
        self.hike.guides.add(guide)
        response = self.client.get(self.hike.get_absolute_url())
        self.assertContains(response, 'Second guide')
        self.assertContains(response, 'Experienced local guide')
        self.assertEqual(self.client.get(reverse('hikes:list')).context['guide_count'], 2)

    def test_incomplete_publication_is_rejected_and_drafts_are_private(self):
        draft = Hike.objects.create(title='Private draft', **self.fields)
        with self.assertRaises(ValidationError):
            draft.publish()
        self.assertEqual(self.client.get(draft.get_absolute_url()).status_code, 404)
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse('bookings:book_hike', args=[draft.pk])).status_code, 404)
        form = HikeAdminForm(data={**self.fields, 'title': 'Incomplete public trail',
                                  'is_published': True, 'status': 'scheduled', 'reserved_spots': 0})
        self.assertFalse(form.is_valid())
        self.assertIn('guides', form.errors)
        self.assertIn('departure_time', form.errors)
        draft.departure_time = time(8)
        draft.save()
        draft.guides.add(self.hike.guides.first())
        draft.publish()
        self.assertEqual(self.client.get(draft.get_absolute_url()).status_code, 200)

    def test_saving_is_idempotent_private_and_requires_post_and_login(self):
        save = reverse('hikes:save', args=[self.hike.pk])
        self.assertEqual(self.client.post(save).status_code, 302)
        self.assertEqual(SavedHike.objects.count(), 0)
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(save).status_code, 405)
        self.client.post(save)
        self.client.post(save)
        self.assertEqual(SavedHike.objects.count(), 1)
        with self.assertRaises(IntegrityError), transaction.atomic():
            SavedHike.objects.create(user=self.user, hike=self.hike)
        self.client.force_login(self.other)
        self.assertNotContains(self.client.get(reverse('hikes:saved')), self.hike.title)
        self.client.post(reverse('hikes:unsave', args=[self.hike.pk]))
        self.assertEqual(SavedHike.objects.count(), 1)
        self.client.force_login(self.user)
        self.client.post(reverse('hikes:unsave', args=[self.hike.pk]))
        self.assertFalse(SavedHike.objects.exists())

    def test_saved_list_does_not_disclose_unpublished_hike(self):
        SavedHike.objects.create(user=self.user, hike=self.hike)
        self.hike.is_published = False
        self.hike.save(update_fields=['is_published'])
        self.client.force_login(self.user)
        response = self.client.get(reverse('hikes:saved'))
        self.assertContains(response, 'Hike currently unavailable')
        self.assertNotContains(response, self.hike.title)

    def test_announcements_are_public_scoped_and_escape_text(self):
        Announcement.objects.create(title='General update', body='<script>test</script>', is_published=True)
        Announcement.objects.create(title='Specific update', body='Trail information', hike=self.hike, is_published=True)
        Announcement.objects.create(title='Draft announcement', body='Private', hike=self.hike)
        response = self.client.get(reverse('hikes:announcements'))
        self.assertContains(response, 'General update')
        self.assertContains(response, 'Specific update')
        self.assertContains(response, '&lt;script&gt;test&lt;/script&gt;')
        self.assertNotContains(response, 'Draft announcement')
        self.assertContains(self.client.get(self.hike.get_absolute_url()), 'Specific update')
        self.hike.is_published = False
        self.hike.save(update_fields=['is_published'])
        self.assertNotContains(self.client.get(reverse('hikes:announcements')), 'Specific update')

    def test_admin_can_cancel_and_postpone_but_members_cannot(self):
        self.reservation()
        url = reverse('admin:hikes_hike_changelist')
        self.client.force_login(self.user)
        self.assertEqual(self.client.post(url, {'action': 'cancel_hikes', '_selected_action': [self.hike.pk]}).status_code, 302)
        self.hike.refresh_from_db()
        self.assertEqual(self.hike.status, Hike.Status.SCHEDULED)
        self.client.force_login(self.staff)
        data = {'action': 'postpone_hikes', '_selected_action': [self.hike.pk]}
        self.assertContains(self.client.post(url, data), 'Save new schedule')
        data.update(apply='1', date=self.hike.date + timedelta(days=1), departure_time='09:00', reason='Weather')
        self.assertEqual(self.client.post(url, data).status_code, 302)
        self.hike.refresh_from_db()
        self.assertEqual(self.hike.status, Hike.Status.POSTPONED)
        self.assertEqual(self.client.post(url, {'action': 'cancel_hikes', '_selected_action': [self.hike.pk]}).status_code, 302)
        self.hike.refresh_from_db()
        self.assertEqual(self.hike.status, Hike.Status.CANCELLED)

    def test_admin_schedule_edit_records_actor_and_notifies(self):
        self.reservation()
        self.client.force_login(self.staff)
        data = {**self.fields, 'title': self.hike.title, 'date': self.hike.date + timedelta(days=1),
                'departure_time': '10:00', 'status': 'scheduled', 'is_published': 'on',
                'guides': [self.hike.guides.first().pk], 'status_reason': 'Route update', 'elevation_m': 0,
                'photos-TOTAL_FORMS': '0', 'photos-INITIAL_FORMS': '0',
                'changes-TOTAL_FORMS': '0', 'changes-INITIAL_FORMS': '0', '_save': 'Save'}
        response = self.client.post(reverse('admin:hikes_hike_change', args=[self.hike.pk]), data)
        if response.status_code != 302:
            self.fail(str(response.context['adminform'].form.errors) + str([
                (inline.formset.prefix, inline.formset.errors, inline.formset.non_form_errors())
                for inline in response.context['inline_admin_formsets']]))
        self.assertEqual(self.hike.changes.get().changed_by_id, self.staff.pk)
        self.assertEqual(BookingNotification.objects.count(), 1)

    def test_admin_announcement_create_edit_delete_and_permission(self):
        url = reverse('admin:hikes_announcement_add')
        data = dict(title='New public update', body='Some news', is_published='on')
        self.client.force_login(self.user)
        self.assertEqual(self.client.post(url, data).status_code, 302)
        self.assertFalse(Announcement.objects.exists())
        self.client.force_login(self.staff)
        self.assertEqual(self.client.post(url, data).status_code, 302)
        announcement = Announcement.objects.get()
        data['body'] = 'Updated news'
        self.assertEqual(self.client.post(reverse('admin:hikes_announcement_change', args=[announcement.pk]), data).status_code, 302)
        self.assertContains(self.client.get(reverse('hikes:announcements')), 'Updated news')
        self.assertEqual(self.client.post(reverse('admin:hikes_announcement_delete', args=[announcement.pk]),
                                          {'post': 'yes'}).status_code, 302)
        self.assertFalse(Announcement.objects.exists())

    def test_saved_actions_require_csrf(self):
        browser = Client(enforce_csrf_checks=True)
        browser.force_login(self.user)
        self.assertEqual(browser.post(reverse('hikes:save', args=[self.hike.pk])).status_code, 403)
        self.assertFalse(SavedHike.objects.exists())

    def test_direct_publication_without_guides_is_rejected(self):
        draft = Hike.objects.create(title='Draft without a guide', departure_time=time(8), **self.fields)
        draft.is_published = True
        with self.assertRaises(ValidationError):
            draft.save()
        draft.refresh_from_db()
        self.assertFalse(draft.is_published)

    def test_staff_with_view_permission_cannot_run_status_actions(self):
        from django.contrib.auth.models import Permission
        viewer = get_user_model().objects.create_user(username='read-only-admin', is_staff=True)
        viewer.user_permissions.add(Permission.objects.get(codename='view_hike'))
        self.client.force_login(viewer)
        self.client.post(reverse('admin:hikes_hike_changelist'), {
            'action': 'cancel_hikes', '_selected_action': [self.hike.pk],
        })
        self.hike.refresh_from_db()
        self.assertEqual(self.hike.status, Hike.Status.SCHEDULED)
