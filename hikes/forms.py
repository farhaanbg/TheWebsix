from django import forms
from .models import Hike


class HikeFilterForm(forms.Form):
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        locations = Hike.objects.order_by('location').values_list('location', flat=True).distinct()
        self.fields['location'].choices = [('', 'All locations')] + [(value, value) for value in locations]
