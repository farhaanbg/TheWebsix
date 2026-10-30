from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from hikes.models import Hike
from hikes.testing import published_hike
from .models import Booking, BookingParticipant


class BookingTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        # Create a test user.
        User = get_user_model()
        cls.user = User.objects.create_user(
            username="testuser",
            password="testpass123"
        )

        # Create a hike for testing.
        cls.hike = published_hike(
            title="Le Morne Brabant Hike",
            location="Le Morne",
            district="Black River",
            date=timezone.localdate() + timedelta(days=7),
            difficulty=Hike.Difficulty.HARD,
            price=Decimal("1200.00"),
            distance_km=8.5,
            duration_minutes=240,
            capacity=10,
            reserved_spots=0,
        )

    def setUp(self):
        # Log in before each test.
        self.client.login(
            username="testuser",
            password="testpass123"
        )

        self.booking_url = reverse(
            "bookings:book_hike",
            kwargs={"pk": self.hike.pk}
        )

        self.my_bookings_url = reverse("bookings:my_bookings")

    def booking_data(self, spots=2):
        # Prepare booking details and participant information.
        data = {
            "customer_name": "John Smith",
            "spots": str(spots),
            "payment_method": Booking.PaymentMethod.CASH,
            "action": "confirm",
            "participants-TOTAL_FORMS": str(spots),
            "participants-INITIAL_FORMS": "0",
            "participants-MIN_NUM_FORMS": "1",
            "participants-MAX_NUM_FORMS": "20",
        }

        for i in range(spots):
            data[f"participants-{i}-full_name"] = f"Participant {i + 1}"
            data[f"participants-{i}-contact_number"] = "52500001"

        return data

    def test_booking_page_requires_login(self):
        self.client.logout()

        response = self.client.get(self.booking_url)

        self.assertEqual(response.status_code, 302)

    def test_booking_page_loads(self):
        response = self.client.get(self.booking_url)

        self.assertEqual(response.status_code, 200)

    def test_successful_booking(self):
        response = self.client.post(
            self.booking_url,
            self.booking_data()
        )

        self.assertRedirects(response, self.my_bookings_url)

        booking = Booking.objects.get()

        self.assertEqual(booking.user, self.user)
        self.assertEqual(booking.hike, self.hike)
        self.assertEqual(booking.spots, 2)
        self.assertEqual(booking.total_price, Decimal("2400.00"))

        self.assertEqual(BookingParticipant.objects.count(), 2)

        self.hike.refresh_from_db()
        self.assertEqual(self.hike.reserved_spots, 2)

    def test_booking_price_calculation(self):
        data = self.booking_data(spots=2)
        data["action"] = "calculate"

        response = self.client.post(self.booking_url, data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["total_price"],
            Decimal("2400.00")
        )

        self.assertEqual(Booking.objects.count(), 0)

    def test_cannot_book_more_spots_than_available(self):
        response = self.client.post(
            self.booking_url,
            self.booking_data(spots=11)
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Booking.objects.count(), 0)

        self.hike.refresh_from_db()
        self.assertEqual(self.hike.reserved_spots, 0)

    def test_missing_participant_details_are_rejected(self):
        data = self.booking_data(spots=1)
        data["participants-0-full_name"] = ""
        data["participants-0-contact_number"] = ""

        response = self.client.post(self.booking_url, data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Booking.objects.count(), 0)
        self.assertEqual(BookingParticipant.objects.count(), 0)

    def test_my_bookings_page_loads(self):
        # Create a booking belonging to the logged-in user.
        booking = Booking.objects.create(
            user=self.user,
            hike=self.hike,
            customer_name="John Smith",
            spots=2,
            payment_method=Booking.PaymentMethod.CASH,
            total_price=Decimal("2400.00"),
        )

        response = self.client.get(self.my_bookings_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Le Morne Brabant Hike")
        self.assertContains(response, "2400")

    def test_users_only_see_their_own_bookings(self):
        # Create a second user.
        User = get_user_model()
        other_user = User.objects.create_user(
            username="otheruser",
            password="otherpass123"
        )

        # Create a booking belonging to the second user.
        Booking.objects.create(
            user=other_user,
            hike=self.hike,
            customer_name="Other Customer",
            spots=1,
            payment_method=Booking.PaymentMethod.CASH,
            total_price=Decimal("1200.00"),
        )

        # The logged-in user should not see the other user's booking.
        response = self.client.get(self.my_bookings_url)

        self.assertNotContains(response, "Other Customer")

    def test_blank_second_participant_returns_validation_error(self):
        data = self.booking_data(spots=2)
        data['participants-1-full_name'] = ''
        data['participants-1-contact_number'] = ''
        response = self.client.post(self.booking_url, data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Enter details for every participant.')
        self.assertFalse(Booking.objects.exists())
        self.hike.refresh_from_db()
        self.assertEqual(self.hike.reserved_spots, 0)

    def test_participant_count_must_match_requested_spots(self):
        data = self.booking_data(spots=1)
        data['spots'] = '2'
        response = self.client.post(self.booking_url, data)
        self.assertContains(response, 'participant fields do not match')
        self.assertFalse(Booking.objects.exists())

    def test_calculate_enforces_twenty_participant_limit(self):
        self.hike.capacity = 30
        self.hike.save(update_fields=['capacity'])
        data = self.booking_data(spots=21)
        data['action'] = 'calculate'
        response = self.client.post(self.booking_url, data)
        self.assertIn('spots', response.context['form'].errors)
        self.assertLessEqual(len(response.context['participant_formset'].forms), 20)
        self.assertFalse(Booking.objects.exists())

    def test_fully_booked_hike_rejects_direct_submission(self):
        self.hike.reserved_spots = self.hike.capacity
        self.hike.save(update_fields=['reserved_spots'])
        response = self.client.post(self.booking_url, self.booking_data())
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Booking.objects.exists())
        detail = self.client.get(self.hike.get_absolute_url())
        self.assertContains(detail, 'Fully booked')
        self.assertNotContains(detail, 'Book this hike')

    def test_past_hike_rejects_booking_and_hides_booking_link(self):
        self.hike.date = timezone.localdate() - timedelta(days=1)
        self.hike.save(update_fields=['date'])
        response = self.client.post(self.booking_url, self.booking_data())
        self.assertRedirects(response, self.hike.get_absolute_url())
        self.assertFalse(Booking.objects.exists())
        self.assertNotContains(self.client.get(self.hike.get_absolute_url()), 'Book this hike')

    def test_hike_departure_time_controls_same_day_bookings(self):
        from unittest.mock import patch
        now = timezone.localtime().replace(hour=12, minute=0, second=0, microsecond=0)
        self.hike.date = now.date()
        self.hike.departure_time = now.replace(hour=11).time()
        self.hike.save(update_fields=['date', 'departure_time'])
        with patch('hikes.models.timezone.localtime', return_value=now):
            self.assertRedirects(self.client.post(self.booking_url, self.booking_data()),
                                 self.hike.get_absolute_url())
        self.assertFalse(Booking.objects.exists())

    def test_booking_appears_with_hike_details_on_account_dashboard(self):
        self.client.post(self.booking_url, self.booking_data())
        response = self.client.get(reverse('accounts:account_detail'))
        self.assertContains(response, self.hike.title)
        self.assertContains(response, 'Confirmation pending')
        self.assertContains(response, 'href="' + self.my_bookings_url + '"')
        self.assertEqual(response.context['bookings_count'], 1)
        response = self.client.get(self.my_bookings_url)
        self.assertContains(response, 'aria-current="page">My Bookings')
        self.assertContains(response, 'href="' + reverse('accounts:account_detail') + '"')

    def test_failed_participant_save_rolls_back_booking_and_reserved_spots(self):
        from unittest.mock import patch
        with patch('bookings.views.BookingParticipant.objects.create',
                   side_effect=RuntimeError('save failed')):
            with self.assertRaises(RuntimeError):
                self.client.post(self.booking_url, self.booking_data())
        self.assertFalse(Booking.objects.exists())
        self.assertFalse(BookingParticipant.objects.exists())
        self.hike.refresh_from_db()
        self.assertEqual(self.hike.reserved_spots, 0)
