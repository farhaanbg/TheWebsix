from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from hikes.models import Hike
from hikes.testing import published_hike
from .models import Booking, BookingParticipant


class BookingCapacityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username='capacity-hiker')
        cls.other = get_user_model().objects.create_user(username='another-hiker')
        cls.staff = get_user_model().objects.create_superuser(username='capacity-admin')
        fields = dict(location='Chamarel', date=timezone.localdate() + timedelta(days=7),
                      difficulty='easy', price=Decimal('100.00'), distance_km=5,
                      duration_minutes=90, capacity=10)
        cls.hike = published_hike(title='Forest trail', **fields)
        cls.second = published_hike(title='Waterfall trail', **fields)

    def setUp(self):
        self.client.force_login(self.user)

    def booking(self, spots=2, **kwargs):
        fields = dict(user=self.user, hike=self.hike, spots=spots,
                      customer_name='Hiker', payment_method=Booking.PaymentMethod.CASH)
        fields.update(kwargs)
        return Booking.objects.create(**fields)

    def assert_reserved(self, hike, expected):
        hike.refresh_from_db()
        self.assertEqual(hike.reserved_spots, expected)

    def admin_data(self, booking, **changes):
        data = dict(user=self.user.pk, hike=booking.hike_id, customer_name='Hiker',
                    spots=booking.spots, payment_method=booking.payment_method,
                    status=booking.status, _save='Save')
        data.update(changes)
        return data

    def test_owner_cancellation_releases_spots_and_repeated_post_is_safe(self):
        booking = self.booking()
        url = reverse('bookings:cancel_booking', args=[booking.pk])
        self.assertContains(self.client.get(reverse('bookings:my_bookings')), url)
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assert_reserved(self.hike, 2)
        for _ in range(2):
            self.assertRedirects(self.client.post(url), reverse('bookings:my_bookings'))
            self.assert_reserved(self.hike, 0)
        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.CANCELLED)
        self.assertNotContains(self.client.get(reverse('bookings:my_bookings')), url)
        self.assertContains(self.client.get(self.hike.get_absolute_url()), '10 of 10 spots remaining')

    def test_cancellation_requires_login_and_booking_ownership(self):
        booking = self.booking(user=self.other)
        url = reverse('bookings:cancel_booking', args=[booking.pk])
        self.assertEqual(self.client.post(url).status_code, 404)
        self.client.force_login(self.staff)
        self.assertEqual(self.client.post(url).status_code, 404)
        self.client.logout()
        self.assertEqual(self.client.post(url).status_code, 302)
        self.assert_reserved(self.hike, 2)

    def test_cancellation_requires_csrf_token(self):
        booking = self.booking()
        browser = Client(enforce_csrf_checks=True)
        browser.force_login(self.user)
        self.assertEqual(browser.post(reverse('bookings:cancel_booking', args=[booking.pk])).status_code, 403)
        self.assert_reserved(self.hike, 2)

    def test_confirm_then_cancel_never_counts_capacity_twice(self):
        booking = self.booking()
        booking.status = Booking.Status.CONFIRMED
        booking.save(update_fields=['status'])
        self.assert_reserved(self.hike, 2)
        booking.cancel()
        self.assert_reserved(self.hike, 0)
        booking.delete()
        self.assert_reserved(self.hike, 0)

    def test_stale_instances_cannot_release_spots_twice(self):
        booking = self.booking()
        stale = Booking.objects.get(pk=booking.pk)
        booking.cancel()
        stale.cancel()
        self.assert_reserved(self.hike, 0)

    def test_edit_spots_adjusts_only_difference_and_updates_price(self):
        booking = self.booking()
        booking.spots = 5
        booking.save()
        self.assert_reserved(self.hike, 5)
        self.assertEqual(booking.total_price, Decimal('500.00'))
        booking.spots = 1
        booking.save(update_fields=['spots'])
        self.assert_reserved(self.hike, 1)
        booking.refresh_from_db()
        self.assertEqual(booking.total_price, Decimal('100.00'))

    def test_partial_status_save_ignores_unsaved_spot_changes(self):
        booking = self.booking()
        booking.spots = 9
        booking.status = Booking.Status.CONFIRMED
        booking.save(update_fields=['status'])
        self.assert_reserved(self.hike, 2)
        booking.refresh_from_db()
        self.assertEqual(booking.spots, 2)

    def test_move_booking_releases_old_hike_and_reserves_new_hike(self):
        booking = self.booking()
        booking.hike = self.second
        booking.save(update_fields=['hike'])
        self.assert_reserved(self.hike, 0)
        self.assert_reserved(self.second, 2)

    def test_failed_move_preserves_old_booking_and_both_hike_counts(self):
        booking = self.booking()
        self.booking(spots=10, hike=self.second)
        booking.hike = self.second
        with self.assertRaises(ValidationError):
            booking.save()
        self.assert_reserved(self.hike, 2)
        self.assert_reserved(self.second, 10)
        booking.refresh_from_db()
        self.assertEqual(booking.hike_id, self.hike.pk)

    def test_reactivation_checks_capacity_and_departure(self):
        booking = self.booking()
        booking.cancel()
        full = self.booking(spots=10)
        booking.status = Booking.Status.CONFIRMED
        with self.assertRaises(ValidationError):
            booking.save()
        self.assert_reserved(self.hike, 10)
        full.cancel()
        self.hike.date = timezone.localdate() - timedelta(days=1)
        self.hike.save(update_fields=['date'])
        with self.assertRaises(ValidationError):
            booking.save()
        self.assert_reserved(self.hike, 0)

    def test_bulk_delete_releases_only_active_reservations(self):
        cancelled = self.booking()
        cancelled.cancel()
        active = self.booking(spots=3)
        BookingParticipant.objects.create(booking=active, full_name='Hiker', contact_number='123')
        Booking.objects.all().delete()
        self.assert_reserved(self.hike, 0)
        self.assertFalse(BookingParticipant.objects.exists())

    def test_failed_save_rolls_back_capacity_adjustment(self):
        booking = self.booking()
        booking.spots = 5
        with patch('django.db.models.Model.save', side_effect=RuntimeError('save failed')):
            with self.assertRaises(RuntimeError):
                booking.save()
        self.assert_reserved(self.hike, 2)
        booking.refresh_from_db()
        self.assertEqual(booking.spots, 2)

    def test_direct_bulk_status_update_is_rejected_without_capacity_change(self):
        booking = self.booking()
        with self.assertRaises(ValueError):
            Booking.objects.filter(pk=booking.pk).update(status=Booking.Status.CANCELLED)
        self.assert_reserved(self.hike, 2)

    def test_admin_edits_recalculate_capacity_and_reject_overbooking(self):
        booking = self.booking()
        self.client.force_login(self.staff)
        url = reverse('admin:bookings_booking_change', args=[booking.pk])
        self.assertEqual(self.client.post(url, self.admin_data(booking, spots=4)).status_code, 302)
        self.assert_reserved(self.hike, 4)
        response = self.client.post(url, self.admin_data(booking, spots=11))
        self.assertContains(response, 'not enough available spots')
        self.assert_reserved(self.hike, 4)
        response = self.client.post(url, self.admin_data(booking, status=Booking.Status.CANCELLED))
        self.assertEqual(response.status_code, 302)
        self.assert_reserved(self.hike, 0)

    def test_admin_actions_and_single_delete_keep_capacity_consistent(self):
        booking = self.booking()
        self.client.force_login(self.staff)
        url = reverse('admin:bookings_booking_changelist')
        for action, expected in [('cancel_bookings', 0), ('confirm_bookings', 2)]:
            response = self.client.post(url, {'action': action, '_selected_action': [booking.pk]})
            self.assertEqual(response.status_code, 302)
            self.assert_reserved(self.hike, expected)
        self.assertEqual(self.client.post(reverse('admin:bookings_booking_delete', args=[booking.pk]),
                                          {'post': 'yes'}).status_code, 302)
        self.assert_reserved(self.hike, 0)

    def test_admin_bulk_delete_and_manual_hike_tampering(self):
        booking = self.booking()
        self.client.force_login(self.staff)
        url = reverse('admin:bookings_booking_changelist')
        response = self.client.post(url, {'action': 'delete_selected', '_selected_action': [booking.pk],
                                          'post': 'yes'})
        self.assertEqual(response.status_code, 302)
        self.assert_reserved(self.hike, 0)
        response = self.client.get(reverse('admin:hikes_hike_change', args=[self.hike.pk]))
        self.assertNotIn('reserved_spots', response.context['adminform'].form.fields)

    def test_existing_manual_reservations_are_preserved(self):
        self.hike.reserved_spots = 3
        self.hike.save(update_fields=['reserved_spots'])
        booking = self.booking(spots=2)
        self.assert_reserved(self.hike, 5)
        booking.cancel()
        self.assert_reserved(self.hike, 3)

    def test_cancelled_full_hike_accepts_a_new_booking(self):
        full = self.booking(spots=10)
        self.client.post(reverse('bookings:cancel_booking', args=[full.pk]))
        data = dict(customer_name='Hiker', spots='1', payment_method='cash', action='confirm',
                    **{'participants-TOTAL_FORMS': '1', 'participants-INITIAL_FORMS': '0',
                       'participants-0-full_name': 'Hiker', 'participants-0-contact_number': '123'})
        response = self.client.post(reverse('bookings:book_hike', args=[self.hike.pk]), data)
        self.assertRedirects(response, reverse('bookings:my_bookings'))
        self.assert_reserved(self.hike, 1)
        self.assertEqual(Booking.objects.filter(status=Booking.Status.PENDING).count(), 1)

    def test_admin_saving_stale_hike_does_not_overwrite_reservation_count(self):
        from django.contrib import admin
        from django.test import RequestFactory
        from hikes.admin import HikeAdmin
        stale_hike = Hike.objects.get(pk=self.hike.pk)
        self.booking()
        stale_hike.title = 'Updated trail title'
        request = RequestFactory().post('/')
        request.user = self.staff
        HikeAdmin(Hike, admin.site).save_model(request, stale_hike, None, True)
        self.assert_reserved(self.hike, 2)
        self.assertEqual(self.hike.title, 'Updated trail title')
