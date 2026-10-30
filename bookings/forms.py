
from django import forms
from django.forms import BaseFormSet, formset_factory
from .models import Booking


class BookingForm(forms.Form):

    customer_name = forms.CharField(
        label="Name",
        max_length=150,
        widget=forms.TextInput(attrs={
            "class": "booking-input",
            "placeholder": "Enter your full name",
            "autocomplete": "name",
        })
    )

    spots = forms.IntegerField(
        label="How many spots to book?",
        min_value=1,
        max_value=20,
        widget=forms.NumberInput(attrs={
            "class": "booking-input",
            "min": "1",
            "step": "1",
        })
    )

    payment_method = forms.ChoiceField(
        label="Select payment method",
        choices=Booking.PaymentMethod.choices,
        initial=Booking.PaymentMethod.CASH,
        widget=forms.RadioSelect
    )

    def __init__(self, *args, available_spots=0, **kwargs):
        super().__init__(*args, **kwargs)

        self.available_spots = available_spots

        self.fields["spots"].widget.attrs["max"] = str(
            available_spots
        )

    def clean_spots(self):
        spots = self.cleaned_data["spots"]

        if spots > self.available_spots:
            raise forms.ValidationError(
                f"Only {self.available_spots} spots remain."
            )

        return spots


class ParticipantForm(forms.Form):

    full_name = forms.CharField(
        label="Participant name",
        max_length=150,
        widget=forms.TextInput(attrs={
            "class": "booking-input",
            "placeholder": "Enter participant's full name",
        })
    )

    contact_number = forms.CharField(
        label="Contact number",
        max_length=30,
        widget=forms.TextInput(attrs={
            "class": "booking-input",
            "placeholder": "Enter phone number",
            "type": "tel",
        })
    )


class RequiredParticipantFormSet(BaseFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return
        if any(not data.get("full_name") or not data.get("contact_number")
               for data in self.cleaned_data):
            raise forms.ValidationError("Enter details for every participant.")


# Maximum of 20 participants per booking.
ParticipantFormSet = formset_factory(
    ParticipantForm,
    formset=RequiredParticipantFormSet,
    extra=0,
    min_num=1,
    max_num=20,
    absolute_max=20,
    validate_min=True,
    validate_max=True
)
