from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone


class Question(models.Model):
    """One question asked by a hiker, plus the official answer from the team.

    Requirements covered: FR 1.15, FR 2.52-2.55 and FR 3.44-3.46.
    A question has at most ONE official answer, so the answer is stored on the
    question itself instead of in a separate Answer table.
    """

    # TextChoices gives a fixed list of categories. The form shows it as a
    # drop-down and Django rejects any value that is not in the list.
    class Category(models.TextChoices):
        GENERAL = 'general', 'General'
        HIKES = 'hikes', 'Hikes & trails'
        BOOKINGS = 'bookings', 'Bookings & payment'
        EQUIPMENT = 'equipment', 'Equipment & safety'

    # Many questions can belong to one user (one-to-many relationship).
    # CASCADE: if the user deletes their account, their questions go too.
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                               related_name='qa_questions')
    title = models.CharField(max_length=150)
    details = models.TextField(max_length=1000, blank=True)
    category = models.CharField(max_length=20, choices=Category.choices,
                                default=Category.GENERAL)

    # Filled in by an admin / guide from the Django admin.
    answer = models.TextField(max_length=2000, blank=True)
    # A second ForeignKey to the same User model, so it needs its own
    # related_name. SET_NULL keeps the answer if that admin account is removed.
    answered_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                    null=True, blank=True, related_name='qa_answers')
    answered_at = models.DateTimeField(null=True, blank=True)

    # The admin can hide an inappropriate question without deleting it.
    is_visible = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-pk']   # newest questions first

    def __str__(self):
        # The "toString" method: what the admin and the shell show for this object.
        return self.title

    def get_absolute_url(self):
        return reverse('qa:list') + '#question-' + str(self.id)

    def is_answered(self):
        return bool(self.answer.strip())
    is_answered.boolean = True               # tick / cross icon in the admin list
    is_answered.short_description = 'Answered'

    def author_name(self):
        return self.author.get_full_name().strip() or self.author.get_username()

    def author_initial(self):
        return self.author_name()[:1].upper()

    def answered_by_name(self):
        if self.answered_by is None:
            return 'Dina Arobi team'
        return self.answered_by.get_full_name().strip() or self.answered_by.get_username()

    def save(self, *args, **kwargs):
        # Keep answered_at consistent with the answer text, wherever it is saved from.
        self.answer = self.answer.strip()
        if self.answer and self.answered_at is None:
            self.answered_at = timezone.now()
        if not self.answer:
            self.answered_at = None
            self.answered_by = None
        super().save(*args, **kwargs)
