from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from hikes.models import Hike


class Booking(models.Model):

    # Available payment methods
    class PaymentMethod(models.TextChoices):
        CASH = "cash", "Cash on arrival"
        SCAN = "scan", "Scan-to-Pay"

    # Booking status
    class Status(models.TextChoices):
        PENDING = "pending", "Confirmation pending"
        CONFIRMED = "confirmed", "Booking confirmed"
        CANCELLED = "cancelled", "Booking cancelled"

    # The hike being booked
    hike = models.ForeignKey(
        Hike,
        on_delete=models.PROTECT,
        related_name="bookings"
    )

    # User account that made the booking
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bookings"
    )

    # Person responsible for the booking
    customer_name = models.CharField(max_length=150)

    # Number of places reserved
    spots = models.PositiveIntegerField(
        validators=[MinValueValidator(1)]
    )

    # Selected payment method
    payment_method = models.CharField(
        max_length=10,
        choices=PaymentMethod.choices
    )

    # Total price for all booked places
    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    # Initial status is pending
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.PENDING
    )

    # Date and time the booking was created
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.customer_name} - {self.hike.title}"


class BookingParticipant(models.Model):

    # Each participant belongs to one booking
    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name="participants"
    )

    # Participant's name
    full_name = models.CharField(max_length=150)

    # Participant's contact number
    contact_number = models.CharField(max_length=30)

    def __str__(self):
        return self.full_name