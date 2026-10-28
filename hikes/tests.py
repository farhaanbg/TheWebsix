from datetime import date
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from .models import Hike


class HikePageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.easy = Hike.objects.create(title='Tamarin Falls', location='Henrietta', district='Plaines Wilhems',
            date=date(2027, 1, 8), difficulty='easy', price=200, distance_km=8.6,
            duration_minutes=210, capacity=25, reserved_spots=10, tags='Waterfall, Swimming')
        cls.full = Hike.objects.create(title='Mountain Summit', location='Black River', district='Black River',
            date=date(2027, 1, 1), difficulty='hard', price=450, distance_km=18.2,
            duration_minutes=420, capacity=10, reserved_spots=10)

    def test_listing_includes_full_hikes_and_detail_links(self):
        response = self.client.get(reverse('hikes:list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Fully booked')
        self.assertContains(response, self.full.get_absolute_url())
        self.assertContains(response, '15 of 25 spots remaining')
        self.assertEqual(response.context['available_count'], 1)

    def test_combined_filters_and_zero_price(self):
        response = self.client.get(reverse('hikes:list'), {
            'q': 'falls', 'location': 'Henrietta', 'date': '2027-01-08',
            'max_price': '200', 'difficulty': ['easy', 'moderate'],
        })
        self.assertEqual(list(response.context['hikes']), [self.easy])
        response = self.client.get(reverse('hikes:list'), {'max_price': '0'})
        self.assertContains(response, 'No hikes match your search')
        self.assertEqual(len(response.context['hikes']), 0)

    def test_search_matches_district_and_sorting(self):
        response = self.client.get(reverse('hikes:list'), {'q': 'Plaines'})
        self.assertEqual(list(response.context['hikes']), [self.easy])
        response = self.client.get(reverse('hikes:list'), {'sort': '-price'})
        self.assertEqual(list(response.context['hikes']), [self.full, self.easy])

    def test_invalid_filters_show_errors_without_crashing(self):
        response = self.client.get(reverse('hikes:list'), {'date': 'invalid', 'max_price': '-5', 'sort': 'unknown'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].errors)

    def test_detail_and_missing_hike(self):
        response = self.client.get(self.full.get_absolute_url())
        self.assertContains(response, 'Mountain Summit')
        self.assertContains(response, 'Fully booked')
        self.assertContains(response, 'Online booking is not available yet.')
        self.assertEqual(self.client.get(reverse('hikes:detail', args=[999])).status_code, 404)

    def test_capacity_validation(self):
        self.easy.reserved_spots = self.easy.capacity + 1
        with self.assertRaises(ValidationError):
            self.easy.full_clean()

    def test_empty_listing(self):
        Hike.objects.all().delete()
        self.assertContains(self.client.get(reverse('hikes:list')), 'New adventures are on the way')

    def test_admin_can_create_hike(self):
        user = get_user_model().objects.create_superuser(username='hike-admin', password='test-only-password')
        self.client.force_login(user)
        response = self.client.post(reverse('admin:hikes_hike_add'), {
            'title': 'New admin hike', 'location': 'Chamarel', 'date': '2027-02-01',
            'difficulty': 'moderate', 'price': '300', 'distance_km': '12.4',
            'elevation_m': '847', 'duration_minutes': '270', 'capacity': '20',
            'reserved_spots': '0', '_save': 'Save',
        })
        self.assertEqual(response.status_code, 302)
        self.assertContains(self.client.get(reverse('hikes:list')), 'New admin hike')
