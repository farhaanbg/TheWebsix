from datetime import date
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from .models import Hike
from .testing import published_hike


class HikePageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.easy = published_hike(title='Tamarin Falls', location='Henrietta', district='Plaines Wilhems',
            date=date(2027, 1, 8), difficulty='easy', price=200, distance_km=8.6,
            duration_minutes=210, capacity=25, reserved_spots=10, tags='Waterfall, Swimming')
        cls.full = published_hike(title='Mountain Summit', location='Black River', district='Black River',
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
        self.assertNotContains(response, 'Book this hike')
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
            'departure_time': '08:00', 'status': 'scheduled', 'is_published': 'on',
            'guides': [self.easy.guides.first().pk],
            'photos-TOTAL_FORMS': '0', 'photos-INITIAL_FORMS': '0',
        })
        self.assertEqual(response.status_code, 302)
        self.assertContains(self.client.get(reverse('hikes:list')), 'New admin hike')
class HomeSearchIntegrationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        common = {
            "date": date(2027, 1, 8),
            "distance_km": 5,
            "duration_minutes": 120,
            "capacity": 10,
        }

        cls.free = published_hike(
            title="Coastal Walk",
            location="Flic en Flac",
            district="Black River",
            difficulty="easy",
            price=0,
            **common,
        )

        cls.waterfall = published_hike(
            title="Waterfall Trail",
            location="Henrietta",
            district="Plaines Wilhems",
            difficulty="moderate",
            price="200.50",
            **common,
        )

        cls.expert = published_hike(
            title="Expert Ridge",
            location="Le Morne",
            district="Black River",
            difficulty="expert",
            price=500,
            **common,
        )

    def search(self, **overrides):
        # Match the fields submitted by the home-page form.
        params = {
            "q": "",
            "date": "",
            "difficulty": "",
            "max_price": "",
        }
        params.update(overrides)
        return self.client.get(reverse("hikes:list"), params)

    def test_blank_home_filters_show_all_hikes(self):
        response = self.search()

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["form"].errors)
        self.assertCountEqual(
            response.context["hikes"],
            [self.free, self.waterfall, self.expert],
        )

    def test_search_text_matches_title_location_and_district(self):
        for query in ("waterfall", "henrietta", "plaines"):
            with self.subTest(query=query):
                response = self.search(q=query)

                self.assertFalse(response.context["form"].errors)
                self.assertEqual(
                    list(response.context["hikes"]),
                    [self.waterfall],
                )

    def test_combined_filters_and_inclusive_price_limit(self):
        response = self.search(
            q="Henrietta",
            date="2027-01-08",
            difficulty="moderate",
            max_price="200.50",
        )

        self.assertFalse(response.context["form"].errors)
        self.assertEqual(
            list(response.context["hikes"]),
            [self.waterfall],
        )

        # One cent below the hike's price excludes it.
        response = self.search(
            q="Henrietta",
            date="2027-01-08",
            difficulty="moderate",
            max_price="200.49",
        )
        self.assertFalse(response.context["form"].errors)
        self.assertEqual(list(response.context["hikes"]), [])

    def test_zero_price_returns_only_free_hikes(self):
        response = self.search(max_price="0")

        self.assertFalse(response.context["form"].errors)
        self.assertEqual(list(response.context["hikes"]), [self.free])

    def test_expert_difficulty_is_supported(self):
        response = self.search(difficulty="expert")

        self.assertFalse(response.context["form"].errors)
        self.assertEqual(list(response.context["hikes"]), [self.expert])

    def test_invalid_filters_are_rejected(self):
        cases = [
            ("difficulty", "extreme"),
            ("date", "not-a-date"),
            ("max_price", "-1"),
            ("max_price", "1000000"),
        ]

        for field, value in cases:
            with self.subTest(field=field, value=value):
                response = self.search(**{field: value})

                self.assertEqual(response.status_code, 200)
                self.assertIn(field, response.context["form"].errors)
                self.assertEqual(list(response.context["hikes"]), [])

    def test_listing_still_accepts_multiple_difficulties(self):
        response = self.search(difficulty=["easy", "expert"])

        self.assertFalse(response.context["form"].errors)
        self.assertCountEqual(
            response.context["hikes"],
            [self.free, self.expert],
        )
