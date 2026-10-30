from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.views import PasswordChangeDoneView
from django.db.models import Count
from .forms import SignupForm, EditAccountForm, ProfileForm
from .models import Moment, Comment, UserProfile
from bookings.models import Booking

# -------------------------
# SIGN UP
# -------------------------
def signup(request):
    if request.user.is_authenticated:
        return redirect("accounts:account_detail")

    if request.method == "POST":
        form = SignupForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(request, "Account created! You may now log in.")
            return redirect("accounts:login")
    else:
        form = SignupForm()

    return render(request, "accounts/signup.html", {"form": form})


# -------------------------
# LOGIN
# -------------------------
def login_view(request):
    if request.user.is_authenticated:
        return redirect("accounts:account_detail")

    if request.method == "POST":
        username_or_email = request.POST.get("username")
        password = request.POST.get("password")

        # Allow login using either username or email
        try:
            user = User.objects.get(email=username_or_email)
            username = user.username
        except User.DoesNotExist:
            username = username_or_email

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:
            login(request, user)
            return redirect("accounts:account_detail")
        else:
            messages.error(request, "Invalid username/email or password.")

    return render(request, "accounts/login.html")


# =========================
# ACCOUNT DASHBOARD
# =========================

@login_required
def dashboard_view(request):

    user = request.user

    # Add a new moment
    if request.method == "POST":

        title = request.POST.get("title")
        image_file = request.FILES.get("image_file")
        caption = request.POST.get("caption")
        tag = request.POST.get("tag", "Hike")

        if title and image_file:

            Moment.objects.create(
                user=user,
                title=title,
                image=image_file,
                caption=caption,
                tag=tag
            )

        return redirect("accounts:dashboard")


    # Get user's moments
    moments = Moment.objects.filter(
        user=user
    ).annotate(likes_count=Count("likes"))

    # Get user's bookings
    bookings = Booking.objects.filter(
        user=user
    )

    # Count the users who liked each moment, then total those counts.
    total_likes = moments.aggregate(
        total=Count('likes')
    )['total']

    # Get full name
    full_name = (
        f"{user.first_name} {user.last_name}"
    ).strip()

    if not full_name:
        full_name = user.username

    context = {
        "profile_user": user,
        "full_name": full_name,
        "moments": moments,
        "bookings": bookings,
        "moments_count": moments.count(),
        "bookings_count": bookings.count(),
        "total_likes": total_likes,
    }

    return render(
        request,
        "accounts/details.html",
        context
    )


# =========================
# GET COMMENTS
# =========================

@login_required
def get_comments(request, moment_id):

    moment = get_object_or_404(
        Moment,
        id=moment_id
    )

    comments = moment.comments.select_related(
        "user"
    ).all()

    comments_data = [
        {
            "id": c.id,
            "user": c.user.get_full_name()
                    or c.user.username,
            "text": c.text,
            "created_at": c.created_at.strftime(
                "%b %d, %Y %H:%M"
            ),
            "can_delete": (
                c.user == request.user
                or moment.user == request.user
            )
        }
        for c in comments
    ]

    return JsonResponse({
        "comments": comments_data,
        "moment_title": moment.title
    })

# =========================
# ADD COMMENT
# =========================

@login_required
def add_comment(request, moment_id):

    if request.method != "POST":
        return JsonResponse(
            {"success": False, "error": "POST request required."},
            status=405
        )

    moment = get_object_or_404(Moment, id=moment_id)
    text = request.POST.get("text", "").strip()

    if not text:
        return JsonResponse(
            {"success": False, "error": "Comment cannot be empty."},
            status=400
        )

    comment = Comment.objects.create(
        moment=moment,
        user=request.user,
        text=text
    )

    return JsonResponse({
        "success": True,
        "comment": {
            "id": comment.id,
            "user": comment.user.get_full_name() or comment.user.username,
            "text": comment.text,
            "created_at": comment.created_at.strftime("%b %d, %Y %H:%M"),
            "can_delete": True
        },
        "total_comments": moment.comments.count()
    })

# =========================
# DELETE COMMENT
# =========================

@login_required
def delete_comment(request, comment_id):

    if request.method == "POST":

        comment = get_object_or_404(
            Comment,
            id=comment_id
        )

        if (
            comment.user == request.user
            or comment.moment.user == request.user
        ):

            comment.delete()

            return JsonResponse({
                "success": True
            })

        return JsonResponse(
            {
                "success": False,
                "error": "Unauthorized"
            },
            status=403
        )

    return JsonResponse(
        {
            "success": False
        },
        status=400
    )


@login_required
def edit_account(request):
    # Ensure profile exists for the user
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        user_form = EditAccountForm(
            request.POST,
            instance=request.user
        )
        profile_form = ProfileForm(
            request.POST,
            request.FILES,
            instance=profile
        )

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, "Account updated successfully.")
        else:
            for form in (user_form, profile_form):
                for errors in form.errors.values():
                    for error in errors:
                        messages.error(request, error)

    return redirect("accounts:account_detail")




@login_required
def delete_moment(request, moment_id):

    if request.method == "POST":

        moment = get_object_or_404(
            Moment,
            id=moment_id,
            user=request.user
        )

        moment.delete()

        messages.success(
            request,
            "Moment deleted successfully."
        )

    return redirect("accounts:account_detail")

# -------------------------
# LOGOUT
# -------------------------
@login_required
def logout_view(request):
    logout(request)
    return redirect("accounts:login")


# -------------------------
# CHANGE PASSWORD
# -------------------------
@login_required
def change_password(request):
    if request.method == "POST":
        form = PasswordChangeForm(
            request.user,
            request.POST
        )

        if form.is_valid():
            user = form.save()

            # Keep the user logged in after changing password
            update_session_auth_hash(request, user)

            messages.success(
                request,
                "Password changed successfully."
            )

            return redirect(
                "accounts:password_change_done"
            )
    else:
        form = PasswordChangeForm(request.user)

    return render(
        request,
        "accounts/password_change.html",
        {"form": form}
    )


# -------------------------
# PASSWORD CHANGE COMPLETE
# -------------------------
class CustomPasswordChangeDoneView(PasswordChangeDoneView):
    template_name = "accounts/password_change_done.html"


# -------------------------
# DELETE ACCOUNT
# -------------------------
@login_required
def delete_account(request):
    if request.method == "POST":
        password = request.POST.get("password")

        if request.user.check_password(password):
            request.user.delete()
            messages.success(
                request,
                "Your account has been deleted."
            )
            return redirect("accounts:login")
        else:
            messages.error(
                request,
                "Incorrect password. Try again."
            )

    return render(
        request,
        "accounts/delete_account.html"
    )


@login_required
def toggle_like(request, moment_id):
    if request.method != "POST":
        return JsonResponse(
            {"error": "POST request required."},
            status=405
        )

    moment = get_object_or_404(Moment, id=moment_id)

    if moment.likes.filter(id=request.user.id).exists():
        moment.likes.remove(request.user)
        liked = False
    else:
        moment.likes.add(request.user)
        liked = True

    return JsonResponse({
        "liked": liked,
        "total_likes": moment.likes.count()
    })
