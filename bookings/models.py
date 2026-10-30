from decimal import Decimal

from django.db import models, router, transaction
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db.models import F
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from hikes.models import Hike


class BookingQuerySet(models.QuerySet):
    def update(self, **kwargs):
        if {'hike', 'hike_id', 'spots', 'status'}.intersection(kwargs):
            raise ValueError('Change booking capacity or status through save(), not update().')
        return super().update(**kwargs)

    def bulk_create(self, *args, **kwargs):
        raise ValueError('Create bookings individually so capacity is reserved transactionally.')


class Booking(models.Model):
    objects = BookingQuerySet.as_manager()

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

    @property
    def can_cancel(self):
        return self.status in (self.Status.PENDING, self.Status.CONFIRMED)

    def clean(self):
        super().clean()
        if not self.hike_id or self.spots is None:
            return
        if self.spots < 1:
            raise ValidationError({'spots': 'Reserve at least one spot.'})
        if self.status not in self.Status.values:
            raise ValidationError({'status': 'Choose a valid booking status.'})
        if not self.can_cancel:
            return
        previous = type(self).objects.filter(pk=self.pk).first() if self.pk else None
        hike = Hike.objects.get(pk=self.hike_id)
        previous_spots = (
            previous.spots if previous and previous.can_cancel
            and previous.hike_id == self.hike_id else 0
        )
        if self.spots > previous_spots and not hike.booking_open:
            raise ValidationError({'hike': 'Bookings are closed for this hike.'})
        if self.spots > hike.spots_remaining + previous_spots:
            raise ValidationError({'spots': 'There are not enough available spots for this booking.'})

    def save(self, *args, **kwargs):
        """Keep held capacity and booking changes in the same transaction."""
        using = kwargs.get('using') or router.db_for_write(type(self), instance=self)
        update_fields = kwargs.get('update_fields')
        if update_fields is not None and not update_fields:
            return
        with transaction.atomic(using=using):
            previous = (
                type(self).objects.using(using).filter(pk=self.pk).first()
                if self.pk else None
            )
            # A partial save must not apply unsaved changes to other fields.
            def effective(field):
                name = 'hike_id' if field == 'hike' else field
                if previous and update_fields is not None and not {field, name}.intersection(update_fields):
                    return getattr(previous, name)
                return getattr(self, name)

            hike_id, spots, status = (effective(field) for field in ('hike', 'spots', 'status'))
            if not isinstance(spots, int) or spots < 1:
                raise ValidationError({'spots': 'Reserve at least one spot.'})
            if status not in self.Status.values:
                raise ValidationError({'status': 'Choose a valid booking status.'})
            active = status in (self.Status.PENDING, self.Status.CONFIRMED)
            deltas = {}
            if previous and previous.can_cancel:
                deltas[previous.hike_id] = -previous.spots
            if active:
                deltas[hike_id] = deltas.get(hike_id, 0) + spots
            hike_ids = set(deltas) | {hike_id}
            hikes = {
                hike.pk: hike for hike in Hike.objects.using(using).select_for_update()
                .filter(pk__in=hike_ids).order_by('pk')
            }
            if previous:
                current = type(self).objects.using(using).select_for_update().get(pk=self.pk)
                if (current.hike_id, current.spots, current.status) != (previous.hike_id, previous.spots, previous.status):
                    raise ValidationError('This booking changed while you were editing it. Refresh and try again.')
            for target_id, delta in sorted(deltas.items()):
                if not delta:
                    continue
                target = hikes[target_id]
                query = Hike.objects.using(using).filter(pk=target_id)
                if delta > 0:
                    if not target.booking_open:
                        raise ValidationError({'hike': 'Bookings are closed for this hike.'})
                    query = query.filter(reserved_spots__lte=F('capacity') - delta)
                else:
                    query = query.filter(reserved_spots__gte=-delta)
                if not query.update(reserved_spots=F('reserved_spots') + delta):
                    message = ('There are not enough available spots for this booking.' if delta > 0
                               else 'Reserved spots are inconsistent. Correct the hike before retrying.')
                    raise ValidationError({'spots': message})
            if previous is None or (hike_id, spots) != (previous.hike_id, previous.spots):
                self.total_price = (hikes[hike_id].price * spots).quantize(Decimal('0.01'))
                if update_fields is not None:
                    kwargs['update_fields'] = set(update_fields) | {'total_price'}
            return super().save(*args, **kwargs)

    def cancel(self):
        self.status = self.Status.CANCELLED
        self.save(update_fields=['status'])


@receiver(pre_delete, sender=Booking)
def release_deleted_booking_capacity(sender, instance, using, **kwargs):
    """Also cover admin bulk deletion and queryset deletion."""
    current = sender.objects.using(using).get(pk=instance.pk)
    Hike.objects.using(using).select_for_update().get(pk=current.hike_id)
    locked = sender.objects.using(using).select_for_update().get(pk=instance.pk)
    if locked.hike_id != current.hike_id:
        raise ValidationError('This booking changed. Refresh and retry deletion.')
    current = locked
    if current.can_cancel:
        changed = Hike.objects.using(using).filter(
            pk=current.hike_id, reserved_spots__gte=current.spots,
        ).update(reserved_spots=F('reserved_spots') - current.spots)
        if not changed:
            raise ValidationError('Reserved spots are inconsistent. Correct the hike before retrying.')


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


class BookingNotification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='booking_notifications')
    booking = models.ForeignKey(Booking, on_delete=models.SET_NULL, null=True, related_name='notifications')
    change = models.ForeignKey('hikes.HikeChange', on_delete=models.SET_NULL, null=True)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-pk']
