from django.conf import settings

from home.views import page_not_found


class FriendlyNotFoundMiddleware:
    """Also show the site's 404 page locally, where DEBUG bypasses handler404."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if (
            settings.DEBUG
            and response.status_code == 404
            and response.get("Content-Type", "").startswith("text/html")
            and not response.streaming
        ):
            return page_not_found(request)
        return response
