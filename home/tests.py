from django.contrib.auth import get_user_model
from django.contrib.staticfiles import finders
from django.templatetags.static import static
from django.test import TestCase
from django.urls import resolve, reverse

from .views import home


class HomePageTests(TestCase):
    def test_home_route_and_guest_page(self):
        url = reverse("home")

        self.assertEqual(url, "/")
        self.assertEqual(resolve(url).func, home)

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "home/home.html")
        self.assertTemplateUsed(response, "community/base.html")
        self.assertEqual(response.context["active_class"], "home")
        self.assertEqual(
            response.context["community_nav"]["profile"],
            reverse("accounts:login"),
        )

    def test_signed_in_profile_destination(self):
        user = get_user_model().objects.create_user(
            username="home-test-user",
            password="test-only-password",
        )
        self.client.force_login(user)

        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["community_nav"]["profile"],
            reverse("accounts:account_detail"),
        )

    def test_search_form_still_targets_hike_listing(self):
        response = self.client.get(reverse("home"))

        self.assertContains(
            response,
            '<form class="home-filter" method="get" '
            f'action="{reverse("hikes:list")}">',
        )

        for name in ("q", "date", "difficulty", "max_price"):
            with self.subTest(field=name):
                self.assertContains(response, f'name="{name}"')

        self.assertContains(
            response,
            '<option value="expert">Expert</option>',
            html=True,
        )

    def test_moved_static_assets_are_available(self):
        self.assertIsNotNone(finders.find("home/css/home.css"))
        self.assertIsNotNone(finders.find("home/images/hero.png"))

        response = self.client.get(reverse("home"))

        self.assertContains(response, static("home/css/home.css"))
        self.assertNotContains(response, static("hikes/css/home.css"))