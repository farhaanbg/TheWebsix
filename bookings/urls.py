from django.urls import path
from . import views

app_name = "bookings"

urlpatterns = [
    path(
        "hike/<int:pk>/book/",
        views.book_hike,
        name="book_hike",
    ),
    path(
        "my-bookings/",
        views.my_bookings,
        name="my_bookings",
    ),
]