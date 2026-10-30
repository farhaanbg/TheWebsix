from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone


class Hike(models.Model):
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
    reserved_spots = models.PositiveIntegerField(default=0, help_text='Update manually until booking integration is added.')
    guide = models.CharField(max_length=150, blank=True)
    tags = models.CharField(max_length=200, blank=True, help_text='Separate tags with commas, e.g. Waterfall, Swimming.')
    description = models.TextField(blank=True)

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
