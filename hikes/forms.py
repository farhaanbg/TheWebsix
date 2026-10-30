from django import forms
from django.utils import timezone
from .models import Hike


class HikeFilterForm(forms.Form):
    scope = forms.ChoiceField(required=False, choices=[('upcoming', 'Upcoming hikes'), ('all', 'All hikes and past events')])
    q = forms.CharField(required=False, max_length=150, label='Search hikes',
                        widget=forms.TextInput(attrs={'placeholder': 'Search by trail name, location, or district...'}))
    location = forms.ChoiceField(required=False, choices=(), label='Location')
    date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    max_price = forms.DecimalField(required=False, min_value=0, max_digits=8, decimal_places=2,
                                  label='Maximum price (Rs)', widget=forms.NumberInput(attrs={'placeholder': 'Any price'}))
    difficulty = forms.MultipleChoiceField(required=False, choices=Hike.Difficulty.choices,
                                          widget=forms.CheckboxSelectMultiple)
    sort = forms.ChoiceField(required=False, label='Sort by', choices=[
        ('date', 'Date: soonest'), ('price', 'Price: low to high'),
        ('-price', 'Price: high to low'), ('title', 'Name: A to Z'),
    ])

    def __init__(self, *args, hikes=None, **kwargs):
        super().__init__(*args, **kwargs)
        hikes = Hike.objects.public().upcoming() if hikes is None else hikes
        locations = hikes.order_by('location').values_list('location', flat=True).distinct()
        self.fields['location'].choices = [('', 'All locations')] + [(value, value) for value in locations]


class HikeAdminForm(forms.ModelForm):
    class Meta:
        model = Hike
        fields = '__all__'

    def clean(self):
        data = super().clean()
        self.instance._publishing_guides = bool(data.get('guides'))
        if data.get('is_published'):
            if not data.get('guides'):
                self.add_error('guides', 'Assign at least one guide before publishing.')
            if not data.get('departure_time'):
                self.add_error('departure_time', 'Set the departure time before publishing.')
        if self.instance.pk and data.get('status') == Hike.Status.POSTPONED:
            previous = Hike.objects.get(pk=self.instance.pk)
            if previous.status != Hike.Status.POSTPONED and (
                data.get('date'), data.get('departure_time')
            ) == (previous.date, previous.departure_time):
                self.add_error('date', 'Choose a new date or departure time when postponing a hike.')
        return data


class PostponeHikesForm(forms.Form):
    date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    departure_time = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time'}))
    reason = forms.CharField(max_length=300, widget=forms.Textarea)

    def clean(self):
        data = super().clean()
        date, time = data.get('date'), data.get('departure_time')
        now = timezone.localtime()
        if date and time and (date, time) <= (now.date(), now.time()):
            raise forms.ValidationError('Choose a future date and departure time.')
        return data
