from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    handle = models.CharField(
        max_length=50,
        blank=True
    )
    avatar = models.ImageField(
        upload_to='avatars/',
        blank=True,
        null=True
    )
    cover_image = models.ImageField(
        upload_to='covers/',
        blank=True,
        null=True
    )

    def __str__(self):
        return self.user.get_full_name() or self.user.username


class Moment(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='moments'
    )
    title = models.CharField(max_length=150)
    tag = models.CharField(
        max_length=50,
        default='Hike'
    )
    image = models.ImageField(
        upload_to='moments/'
    )
    caption = models.TextField(blank=True)
 
    likes = models.ManyToManyField(
        User,
        related_name='liked_moments',
        blank=True
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} by {self.user.username}"

    def total_likes(self):
        return self.likes.count()


class Comment(models.Model):
    moment = models.ForeignKey(
        Moment,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    text = models.TextField()
    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.user.username} on {self.moment.title}"


class Booking(models.Model):
    STATUS_CHOICES = [
        ('CONFIRMED', 'Confirmed'),
        ('PENDING', 'Pending'),
        ('CANCELLED', 'Cancelled'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='account_bookings'
    )
    reference_code = models.CharField(
        max_length=20,
        unique=True
    )
    title = models.CharField(max_length=150)
    date_str = models.CharField(max_length=100)
    guide_name = models.CharField(max_length=100)
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='PENDING'
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ['-created_at']

  
    def __str__(self):
        return f"{self.reference_code} - {self.title}"