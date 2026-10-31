from django.contrib import admin
from django.utils import timezone

from .models import Question


class AnsweredFilter(admin.SimpleListFilter):
    # Custom right-hand filter: "Answered: Yes / No".
    title = 'answered'
    parameter_name = 'answered'

    def lookups(self, request, model_admin):
        return (('yes', 'Yes'), ('no', 'No — needs an answer'))

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.exclude(answer='')
        if self.value() == 'no':
            return queryset.filter(answer='')
        return queryset


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    """Admin / guide side of Q&A: view (FR 3.44), answer (FR 3.45), manage (FR 3.46)."""
    list_display = ('title', 'author', 'category', 'is_answered', 'is_visible', 'created_at')
    list_filter = (AnsweredFilter, 'category', 'is_visible', 'created_at')
    list_editable = ('is_visible',)          # hide / show straight from the list
    search_fields = ('title', 'details', 'answer', 'author__username')
    readonly_fields = ('author', 'created_at', 'answered_by', 'answered_at')
    fieldsets = (
        ('Question', {'fields': ('author', 'title', 'category', 'details', 'created_at')}),
        ('Official answer', {'fields': ('answer', 'answered_by', 'answered_at')}),
        ('Moderation', {'fields': ('is_visible',)}),
    )
    actions = ('hide_questions', 'show_questions')

    def has_add_permission(self, request):
        # Questions come from hikers on the website; the admin only answers them.
        return False

    def save_model(self, request, obj, form, change):
        # Record WHICH admin answered, and when, as soon as the answer changes.
        if 'answer' in form.changed_data and obj.answer.strip():
            obj.answered_by = request.user
            obj.answered_at = timezone.now()
        super().save_model(request, obj, form, change)

    @admin.action(description='Hide selected questions from the public page')
    def hide_questions(self, request, queryset):
        queryset.update(is_visible=False)

    @admin.action(description='Show selected questions on the public page')
    def show_questions(self, request, queryset):
        queryset.update(is_visible=True)
