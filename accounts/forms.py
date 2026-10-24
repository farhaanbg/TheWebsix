from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import UserProfile

class SignupForm(UserCreationForm):

    full_name = forms.CharField(
        max_length=150,
        required=True
    )

    class Meta:
        model = User
        fields = [
            'full_name',
            'username',
            'email',
            'password1',
            'password2'
        ]

    def save(self, commit=True):
        user = super().save(commit=False)

        name = self.cleaned_data['full_name'].strip().split(" ", 1)

        user.first_name = name[0]

        if len(name) > 1:
            user.last_name = name[1]

        if commit:
            user.save()

        return user


class EditAccountForm(forms.ModelForm):

    full_name = forms.CharField(
        max_length=150,
        required=True
    )

    class Meta:
        model = User
        fields = [
            'full_name',
            'username',
            'email'
        ]

    def save(self, commit=True):
        user = super().save(commit=False)

        name = self.cleaned_data['full_name'].strip().split(" ", 1)

        user.first_name = name[0]

        if len(name) > 1:
            user.last_name = name[1]

        if commit:
            user.save()

        return user


class ProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['avatar', 'cover_image']
