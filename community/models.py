from django.db import models

# Create your models here.
from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse


RATING_CHOICES = (
    (1, '1 star'),
    (2, '2 stars'),
    (3, '3 stars'),
    (4, '4 stars'),
    (5, '5 stars'),
)


def post_image_path(instance, filename):
    # Compatibility only: the OLD 0001 migration imports this function.
    # if removed, images will be stored in the simpler path below.
    return f"community/{uuid4().hex}{Path(filename).suffix.lower()}"


class Review(models.Model):
    # The original design collects general feedback, not a review of a booking.
    
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                               null=True, blank=True, related_name='community_reviews')
    name = models.CharField(max_length=100)
    rating = models.PositiveSmallIntegerField(
        choices=RATING_CHOICES, default=5,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    text = models.TextField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-pk']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(rating__gte=1, rating__lte=5),
                name='community_review_rating_1_to_5',
            ),
        ]

    def __str__(self):
        return self.name + ': ' + str(self.rating) + '/5'


class Post(models.Model):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                               related_name='community_posts')
    caption = models.TextField(max_length=2000)
    # Same upload_to date-folder technique as House.house_image in class.
    image = models.ImageField(upload_to='community/%Y/%m/%d/', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    # Same technique as House.renters = ManyToManyField('Renter', through='Rental').
    liked_by = models.ManyToManyField(settings.AUTH_USER_MODEL, through='PostLike',
                                     related_name='liked_community_posts', blank=True)

    class Meta:
        ordering = ['-created_at', '-pk']

    def __str__(self):
        return self.caption[:70]

    def get_absolute_url(self):
        # Same reverse(..., args=[str(self.id)]) pattern as House/Renter.
        return reverse('community:post-detail', args=[str(self.id)])

    def author_name(self):
        # Django templates call this no-argument method without parentheses.
        return self.author.get_full_name().strip() or self.author.get_username()

    def author_initial(self):
        return self.author_name()[:1].upper()


class Comment(models.Model):
    # One post can have many comments (a ForeignKey, not a ManyToManyField).
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                               related_name='community_comments')
    text = models.TextField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at', 'pk']

    def __str__(self):
        return self.text[:70]

    def author_name(self):
        return self.author.get_full_name().strip() or self.author.get_username()

    def author_initial(self):
        return self.author_name()[:1].upper()


class PostLike(models.Model):
    # Like Rental, this intermediate model contains TWO ForeignKey fields.
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name='community_post_likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # One person must not create several likes on the same post.
        constraints = [
            models.UniqueConstraint(fields=['post', 'user'],
                                    name='community_one_like_per_user_per_post'),
        ]

    def __str__(self):
        return 'User ' + str(self.user_id) + ' likes post ' + str(self.post_id)
