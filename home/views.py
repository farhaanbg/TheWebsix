from django.shortcuts import render
from django.urls import reverse


def home(request):
    """Display the public home page."""

    if request.user.is_authenticated:
        profile_url = reverse("accounts:account_detail")
    else:
        profile_url = reverse("accounts:login")

    context = {
        "active_class": "home",
        "community_nav": {
            "home": reverse("home"),
            "hikes": reverse("hikes:list"),
            "profile": profile_url,
        },
    }

    return render(request, "home/home.html", context)
