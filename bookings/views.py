
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from hikes.models import Hike
from .forms import BookingForm, ParticipantFormSet
from .models import Booking, BookingParticipant


@login_required
def book_hike(request, pk):

    # Find the selected hike.
    hike = get_object_or_404(Hike.objects.public(), pk=pk)
    if not hike.booking_open:
        messages.error(request, "Bookings are closed for this hike.")
        return redirect("hikes:detail", pk=pk)

    available_spots = hike.spots_remaining

    # Set the default booking to one spot.
    selected_spots = 1

    # Calculate the initial total price.
    total_price = (
        hike.price * Decimal(selected_spots)
    ).quantize(Decimal("0.01"))

    if request.method == "POST":

        # Validate the main booking form.
        form = BookingForm(
            request.POST,
            available_spots=available_spots,
        )

        action = request.POST.get("action")

        # Safely retrieve the selected number of spots.
        try:
            selected_spots = max(
                1,
                min(int(request.POST.get("spots", 1)), 20),
            )
        except (TypeError, ValueError):
            selected_spots = 1

        # Use the validated number of spots when possible.
        if form.is_valid():
            selected_spots = form.cleaned_data["spots"]

        # Calculate the total price.
        total_price = (
            hike.price * Decimal(selected_spots)
        ).quantize(Decimal("0.01"))

        # --------------------------------
        # CALCULATE TOTAL
        # --------------------------------

        if action == "calculate":

            # Copy submitted data to preserve participant details.
            post_data = request.POST.copy()

            # Generate one participant form for each spot.
            post_data["participants-TOTAL_FORMS"] = str(
                selected_spots
            )

            if "participants-INITIAL_FORMS" not in post_data:
                post_data["participants-INITIAL_FORMS"] = "0"

            participant_formset = ParticipantFormSet(
                post_data,
                prefix="participants",
            )

        # --------------------------------
        # CONFIRM BOOKING
        # --------------------------------

        elif action == "confirm":

            participant_formset = ParticipantFormSet(
                request.POST,
                prefix="participants",
            )

            if form.is_valid() and participant_formset.is_valid():

                # Check that participant forms match the spots.
                if len(participant_formset.forms) != selected_spots:

                    form.add_error(
                        "spots",
                        "The participant fields do not match the "
                        "number of spots. Please calculate again.",
                    )

                else:

                    try:
                        with transaction.atomic():
                            booking = Booking.objects.create(
                                user=request.user,
                                hike=hike,
                                customer_name=form.cleaned_data["customer_name"],
                                spots=selected_spots,
                                payment_method=form.cleaned_data["payment_method"],
                                status=Booking.Status.PENDING,
                            )
                            for participant_form in participant_formset:
                                BookingParticipant.objects.create(
                                    booking=booking,
                                    full_name=participant_form.cleaned_data["full_name"],
                                    contact_number=participant_form.cleaned_data["contact_number"],
                                )
                    except ValidationError as error:
                        form.add_error(None, "; ".join(error.messages))
                        hike.refresh_from_db()
                        available_spots = hike.spots_remaining
                    else:
                        messages.success(
                            request,
                            f"Booking #{booking.pk} submitted. Confirmation is pending.",
                        )
                        return redirect("bookings:my_bookings")

        else:

            # Preserve participant details for other POST actions.
            participant_formset = ParticipantFormSet(
                request.POST,
                prefix="participants",
            )

    else:

        # --------------------------------
        # INITIAL PAGE LOAD
        # --------------------------------

        form = BookingForm(
            available_spots=available_spots,
            initial={"spots": 1},
        )

        participant_formset = ParticipantFormSet(
            prefix="participants",
            initial=[{}],
        )

    # Recalculate total using validated spots when available.
    if request.method == "POST" and form.is_valid():

        selected_spots = form.cleaned_data["spots"]

        total_price = (
            hike.price * Decimal(selected_spots)
        ).quantize(Decimal("0.01"))

    # Page information.
    context = {
        "hike": hike,
        "form": form,
        "participant_formset": participant_formset,
        "available_spots": available_spots,
        "selected_spots": selected_spots,
        "total_price": total_price,

        "community_nav": {
            "home": reverse("home"),
            "hikes": reverse("hikes:list"),
            "profile": reverse(
                "accounts:account_detail"
                if request.user.is_authenticated
                else "accounts:login"
            ),
        },

        "active_class": "hikes",
    }

    return render(
        request,
        "bookings/booking.html",
        context,
    )


@login_required
def my_bookings(request):

    # Retrieve only bookings belonging to the logged-in user.
    bookings = (
        Booking.objects
        .filter(user=request.user)
        .select_related("hike")
        .prefetch_related("participants")
        .order_by("-created_at")
    )

    # Get today's date.
    today = timezone.localdate()

    # Separate upcoming and past bookings.
    current_bookings = bookings.filter(
        hike__date__gte=today
    )

    past_bookings = bookings.filter(
        hike__date__lt=today
    )

    return render(
        request,
        "bookings/my_bookings.html",
        {
            "current_bookings": current_bookings,
            "past_bookings": past_bookings,
            "community_nav": {"home": reverse("home")},
            "active_class": "bookings",
            "notifications": request.user.booking_notifications.select_related('booking')[:50],
        },
    )


@login_required
@require_POST
def cancel_booking(request, pk):
    booking = get_object_or_404(Booking, pk=pk, user=request.user)
    try:
        booking.cancel()
    except ValidationError as error:
        messages.error(request, "; ".join(error.messages))
    else:
        messages.success(request, f"Booking #{booking.pk} cancelled. Your spots have been released.")
    return redirect("bookings:my_bookings")
