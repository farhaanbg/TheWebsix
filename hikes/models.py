from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.conf import settings
from django.db import models, router, transaction
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone


class Guide(models.Model):
    name = models.CharField(max_length=150, unique=True)
    biography = models.TextField(blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class HikeQuerySet(models.QuerySet):
    def public(self):
        return self.filter(is_published=True, departure_time__isnull=False, guides__isnull=False).distinct()

    def upcoming(self):
        now = timezone.localtime()
        return self.filter(Q(date__gt=now.date()) | Q(date=now.date(), departure_time__gt=now.time()))

    def update(self, **kwargs):
        if {'date', 'departure_time', 'status'}.intersection(kwargs):
            raise ValueError('Save hike schedule/status changes individually to record history and notifications.')
        return super().update(**kwargs)


class Hike(models.Model):
    objects = HikeQuerySet.as_manager()

    class Status(models.TextChoices):
        SCHEDULED = 'scheduled', 'Scheduled'
        POSTPONED = 'postponed', 'Postponed'
        CANCELLED = 'cancelled', 'Cancelled'

    class Difficulty(models.TextChoices):
        EASY = 'easy', 'Easy'
        MODERATE = 'moderate', 'Moderate'
        HARD = 'hard', 'Hard'
        EXPERT = 'expert', 'Expert'

    title = models.CharField(max_length=150)
    location = models.CharField(max_length=150)
    district = models.CharField(max_length=100, blank=True)
    date = models.DateField()
    departure_time = models.TimeField(blank=True, null=True)
    difficulty = models.CharField(max_length=10, choices=Difficulty.choices)
    price = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(0)])
    image = models.ImageField(upload_to='hikes/', blank=True)
    distance_km = models.DecimalField(max_digits=6, decimal_places=1, validators=[MinValueValidator(0)])
    elevation_m = models.PositiveIntegerField(default=0)
    duration_minutes = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    capacity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    reserved_spots = models.PositiveIntegerField(default=0, help_text='Updated automatically by bookings. Existing manual reservations are retained.')
    guides = models.ManyToManyField(Guide, related_name='hikes', blank=True)
    is_published = models.BooleanField(default=False, help_text='Publish after assigning guides and a departure time.')
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.SCHEDULED)
    status_reason = models.CharField(max_length=300, blank=True)
    tags = models.CharField(max_length=200, blank=True, help_text='Separate tags with commas, e.g. Waterfall, Swimming.')
    description = models.TextField(blank=True)
    highlights = models.TextField(blank=True, help_text='One highlight per line.')
    what_to_bring = models.TextField(blank=True, help_text='One item per line.')
    meeting_point = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ['date', 'pk']
        constraints = [
            models.CheckConstraint(condition=models.Q(reserved_spots__lte=models.F('capacity')), name='hike_reservations_within_capacity'),
            models.CheckConstraint(condition=models.Q(capacity__gte=1), name='hike_positive_capacity'),
        ]

    def __str__(self):
        return self.title

    def clean(self):
        super().clean()
        if self.capacity is not None and self.reserved_spots is not None and self.reserved_spots > self.capacity:
            raise ValidationError({'reserved_spots': 'Reserved spots cannot exceed capacity.'})
        if self.is_published and self.departure_time is None:
            raise ValidationError({'departure_time': 'A published hike needs a departure time.'})
        if self.is_published and not (getattr(self, '_publishing_guides', False)
                                      or self.pk and self.guides.exists()):
            raise ValidationError({'guides': 'Assign at least one guide before publishing.'})

    def save(self, *args, **kwargs):
        using = kwargs.get('using') or router.db_for_write(type(self), instance=self)
        fields = kwargs.get('update_fields')
        if fields is not None and not fields:
            return
        with transaction.atomic(using=using):
            previous = (type(self).objects.using(using).select_for_update().filter(pk=self.pk).first()
                        if self.pk else None)
            if previous:
                for name in ('date', 'departure_time', 'status', 'status_reason', 'is_published'):
                    if fields is not None and name not in fields:
                        setattr(self, name, getattr(previous, name))
                if fields is None or 'reserved_spots' not in fields:
                    self.reserved_spots = previous.reserved_spots
                schedule_changed = (self.date, self.departure_time) != (previous.date, previous.departure_time)
                if schedule_changed and self.status != self.Status.CANCELLED:
                    self.status = self.Status.POSTPONED
                    if fields is not None:
                        kwargs['update_fields'] = set(fields) | {'status'}
            else:
                schedule_changed = False
            if self.status not in self.Status.values:
                raise ValidationError({'status': 'Choose a valid hike status.'})
            if self.is_published and self.departure_time is None:
                raise ValidationError({'departure_time': 'A published hike needs a departure time.'})
            if self.is_published and not (getattr(self, '_publishing_guides', False)
                                          or self.pk and self.guides.exists()):
                raise ValidationError({'guides': 'Assign at least one guide before publishing.'})
            super().save(*args, **kwargs)
            if previous and (schedule_changed or self.status != previous.status):
                self._record_change(previous, schedule_changed, using)

    def _record_change(self, previous, schedule_changed, using):
        from bookings.models import Booking, BookingNotification
        active = list(Booking.objects.using(using).filter(
            hike_id=self.pk, status__in=[Booking.Status.PENDING, Booking.Status.CONFIRMED],
        ).select_for_update().order_by('pk'))
        change = HikeChange.objects.using(using).create(
            hike=self, old_date=previous.date, old_departure_time=previous.departure_time,
            new_date=self.date, new_departure_time=self.departure_time,
            old_status=previous.status, new_status=self.status, reason=self.status_reason,
            changed_by=getattr(self, '_changed_by', None),
        )
        for booking in active:
            if self.status == self.Status.CANCELLED:
                booking.cancel()
            if booking.user_id:
                label = ('cancelled' if self.status == self.Status.CANCELLED
                         else 'rescheduled' if schedule_changed else self.get_status_display().lower())
                schedule = f'{self.date:%d %b %Y}'
                if self.departure_time:
                    schedule += f' at {self.departure_time:%H:%M}'
                message = f'{self.title} has been {label}. '
                message += ('Your booking has been cancelled.' if self.status == self.Status.CANCELLED
                            else f'The hike is now scheduled for {schedule}. Your booking is retained.')
                if self.status_reason:
                    message += f' {self.status_reason}'
                BookingNotification.objects.using(using).create(
                    user_id=booking.user_id, booking=booking, change=change, message=message,
                )
        self.refresh_from_db(fields=['reserved_spots'])

    def cancel(self, reason='', actor=None):
        self.status = self.Status.CANCELLED
        self.status_reason = reason
        self._changed_by = actor
        self.save(update_fields=['status', 'status_reason'])

    def postpone(self, date, departure_time, reason='', actor=None):
        now = timezone.localtime()
        if not date or not departure_time or (date, departure_time) <= (now.date(), now.time()):
            raise ValidationError('Choose a future date and departure time.')
        if (date, departure_time) == (self.date, self.departure_time):
            raise ValidationError('Choose a new date or departure time.')
        self.date, self.departure_time = date, departure_time
        self.status = self.Status.POSTPONED
        self.status_reason = reason
        self._changed_by = actor
        self.save(update_fields=['date', 'departure_time', 'status', 'status_reason'])

    def publish(self):
        if not self.departure_time or not self.guides.exists():
            raise ValidationError('Assign at least one guide and a departure time before publishing.')
        self.is_published = True
        self.save(update_fields=['is_published'])

    @property
    def guide_names(self):
        return ', '.join(guide.name for guide in self.guides.all())

    @property
    def booking_open(self):
        return (self.status != self.Status.CANCELLED and self.is_published
                and self.departure_time is not None and self.is_upcoming and self.guides.exists())

    def get_absolute_url(self):
        return reverse('hikes:detail', args=[self.pk])

    @property
    def is_upcoming(self):
        now = timezone.localtime()
        return self.date > now.date() or (
            self.date == now.date()
            and (self.departure_time is None or self.departure_time > now.time())
        )

    @property
    def spots_remaining(self):
        return max(0, self.capacity - self.reserved_spots)

    @property
    def availability_percent(self):
        return round(self.spots_remaining / self.capacity * 100) if self.capacity else 0

    @property
    def duration_display(self):
        hours, minutes = divmod(self.duration_minutes, 60)
        return f'{hours}h {minutes:02d}m'

    @property
    def tag_list(self):
        return [tag.strip() for tag in self.tags.split(',') if tag.strip()]

    @property
    def highlight_list(self):
        return [line.strip() for line in self.highlights.splitlines() if line.strip()]

    @property
    def packing_list(self):
        return [line.strip() for line in self.what_to_bring.splitlines() if line.strip()]


class HikePhoto(models.Model):
    hike = models.ForeignKey(Hike, on_delete=models.CASCADE, related_name='photos')
    image = models.ImageField(upload_to='hikes/gallery/')
    caption = models.CharField(max_length=200, blank=True)
    position = models.PositiveIntegerField(default=0, help_text='Lower numbers appear first, after the cover photo.')

    class Meta:
        ordering = ['position', 'pk']

    def __str__(self):
        return self.caption or f'Photo for {self.hike}'


class HikeChange(models.Model):
    hike = models.ForeignKey(Hike, on_delete=models.CASCADE, related_name='changes')
    old_date = models.DateField()
    old_departure_time = models.TimeField(null=True, blank=True)
    new_date = models.DateField()
    new_departure_time = models.TimeField(null=True, blank=True)
    old_status = models.CharField(max_length=12)
    new_status = models.CharField(max_length=12)
    reason = models.CharField(max_length=300, blank=True)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-pk']


class SavedHike(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='saved_hikes')
    hike = models.ForeignKey(Hike, on_delete=models.CASCADE, related_name='saved_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-pk']
        constraints = [models.UniqueConstraint(fields=['user', 'hike'], name='unique_user_saved_hike')]


class Announcement(models.Model):
    title = models.CharField(max_length=150)
    body = models.TextField(max_length=5000)
    hike = models.ForeignKey(Hike, null=True, blank=True, on_delete=models.CASCADE, related_name='announcements')
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-pk']

    def __str__(self):
        return self.title
