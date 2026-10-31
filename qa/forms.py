from django import forms
from django.forms import ModelForm

from .models import Question


class AskQuestionModelForm(ModelForm):
    """The form a logged-in hiker fills in to ask a question.

    Two layers of validation:
    1. HTML5 in the browser: required, minlength and maxlength attributes below.
    2. Django on the server: the clean_... methods, which still run even if
       someone bypasses the browser checks.
    """

    class Meta:
        model = Question
        # author is NOT a field: views.py sets it to request.user,
        # so nobody can post a question in someone else's name.
        # answer / answered_by are NOT fields: only an admin can answer.
        fields = ['title', 'category', 'details']
        labels = {
            'title': 'Your question',
            'category': 'Category',
            'details': 'More details (optional)',
        }
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'da-input',
                'minlength': 10,
                'placeholder': 'e.g. Do I need hiking boots for Le Pouce?',
            }),
            'category': forms.Select(attrs={'class': 'da-input'}),
            'details': forms.Textarea(attrs={
                'class': 'da-input',
                'rows': 3,
                'placeholder': 'Anything that helps us give a better answer...',
            }),
        }

    def __init__(self, *args, user=None, **kwargs):
        # The view passes the logged-in user so clean_title can check duplicates.
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_title(self):
        title = ' '.join(self.cleaned_data['title'].split())   # tidy extra spaces
        if len(title) < 10:
            raise forms.ValidationError('Please write a full question (at least 10 characters).')
        if not title.endswith('?'):
            title += '?'
        if self.user is not None and Question.objects.filter(
                author=self.user, title__iexact=title).exists():
            raise forms.ValidationError('You have already asked this question.')
        return title

    def clean_details(self):
        return self.cleaned_data['details'].strip()


class DeleteQuestionForm(forms.Form):
    # Empty form: it only exists so the delete button is a POST with a CSRF token.
    pass
