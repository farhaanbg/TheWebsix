from django.contrib.auth import get_user_model
from django.contrib.staticfiles import finders
from django.templatetags.static import static
from django.http import HttpResponse, JsonResponse
from django.test import RequestFactory, TestCase, override_settings
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


class NotFoundPageTests(TestCase):
    def assert_friendly_not_found(self, response):
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, "home/404.html")
        self.assertContains(response, "Back to Home", status_code=404)
        self.assertContains(response, f'href="{reverse("home")}"', status_code=404)
        self.assertContains(response, f'href="{reverse("hikes:list")}"', status_code=404)
        self.assertNotContains(response, "URLconf", status_code=404)

    def test_unknown_urls_in_local_and_production_modes(self):
        for debug in (True, False):
            with self.subTest(debug=debug), override_settings(DEBUG=debug):
                self.assert_friendly_not_found(self.client.get("/this-trail-does-not-exist/"))

    def test_missing_record_in_local_and_production_modes(self):
        for debug in (True, False):
            with self.subTest(debug=debug), override_settings(DEBUG=debug):
                self.assert_friendly_not_found(self.client.get("/hikes/999999/"))

    def test_signed_in_account_navigation(self):
        user = get_user_model().objects.create_user(username="lost-hiker")
        self.client.force_login(user)
        response = self.client.get("/unknown-page/")
        self.assert_friendly_not_found(response)
        self.assertContains(response, f'href="{reverse("accounts:account_detail")}"', status_code=404)

    @override_settings(DEBUG=True)
    def test_json_errors_and_server_errors_are_preserved(self):
        from thewebsix.middleware import FriendlyNotFoundMiddleware

        request = RequestFactory().get("/unknown-page/")
        for response in (JsonResponse({"error": "Missing"}, status=404), HttpResponse(status=500)):
            with self.subTest(status=response.status_code):
                middleware = FriendlyNotFoundMiddleware(lambda request: response)
                self.assertIs(middleware(request), response)

    def test_error_stylesheet_is_available(self):
        self.assertIsNotNone(finders.find("home/css/404.css"))
