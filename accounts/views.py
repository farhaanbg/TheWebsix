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
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache
from .forms import SignupForm, EditAccountForm, ProfileForm
from .models import UserProfile
from bookings.models import Booking
from community.models import Post, PostLike, Comment as CommunityComment
from django.utils import timezone
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
@never_cache
def login_view(request):
    next_url = request.POST.get("next") or request.GET.get("next")
    if not url_has_allowed_host_and_scheme(
            next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure()):
        next_url = None

    if request.user.is_authenticated:
        return redirect(next_url or "accounts:account_detail")

    if request.method == "POST":
        username_or_email = request.POST.get("username")
        password = request.POST.get("password")

        # Allow login using either username or email
        try:
            user = User.objects.get(email=username_or_email)
            username = user.username
        except (User.DoesNotExist, User.MultipleObjectsReturned):
            username = username_or_email

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:
            login(request, user)
            return redirect(next_url or "accounts:account_detail")
        else:
            messages.error(request, "Invalid username/email or password.")

    return render(request, "accounts/login.html", {"next": next_url or ""})




# =========================
# ACCOUNT DASHBOARD
# =========================

@login_required
@never_cache
def dashboard_view(request):
    user = request.user

    # Get the user's Community posts
    posts = Post.objects.filter(
        author=user
    ).annotate(
        likes_count=Count("likes", distinct=True)
    ).order_by("-created_at", "-pk")

    # Get the user's bookings
    bookings = Booking.objects.filter(user=user).select_related("hike")

    # Count all likes on the user's posts
    total_likes = sum(post.likes_count for post in posts)

    # Get full name
    full_name = (
        f"{user.first_name} {user.last_name}"
    ).strip()

    if not full_name:
        full_name = user.username

    context = {
        "community_nav": {"home": reverse("home")},
        "profile_user": user,
        "full_name": full_name,
        "moments": posts,
        "bookings": bookings,
        "moments_count": posts.count(),
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
    post = get_object_or_404(Post, id=moment_id)

    comments = post.comments.select_related("author").all()

    comments_data = [
        {
            "id": c.id,
            "user": c.author.get_full_name().strip()
                    or c.author.username,
            "text": c.text,
            "created_at": timezone.localtime(c.created_at).strftime("%b %d, %Y %H:%M"),
            "can_delete": (
                c.author == request.user
                or post.author == request.user
            )
        }
        for c in comments
    ]

    return JsonResponse({
        "comments": comments_data,
        "moment_title": post.caption
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

    post = get_object_or_404(Post, id=moment_id)
    text = request.POST.get("text", "").strip()

    if not text:
        return JsonResponse(
            {"success": False, "error": "Comment cannot be empty."},
            status=400
        )

    comment = CommunityComment.objects.create(
        post=post,
        author=request.user,
        text=text
    )

    return JsonResponse({
        "success": True,
        "comment": {
            "id": comment.id,
            "user": comment.author.get_full_name().strip()
                    or comment.author.username,
            "text": comment.text,
            "created_at": timezone.localtime(comment.created_at).strftime("%b %d, %Y %H:%M"),
            "can_delete": True
        },
        "total_comments": post.comments.count()
    })


# =========================
# DELETE COMMENT
# =========================


@login_required
def delete_comment(request, comment_id):
    if request.method != "POST":
        return JsonResponse(
            {"success": False, "error": "POST request required."},
            status=405
        )

    comment = get_object_or_404(
        CommunityComment.objects.select_related("post", "author"),
        id=comment_id
    )

    # Only the comment author or post owner can delete it
    if (
        comment.author == request.user
        or comment.post.author == request.user
    ):
        post_id = comment.post_id
        comment.delete()

        return JsonResponse({
            "success": True,
            "total_comments": Post.objects.get(id=post_id).comments.count()
        })

    return JsonResponse(
        {"success": False, "error": "Unauthorized"},
        status=403
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
        post = get_object_or_404(
            Post,
            id=moment_id,
            author=request.user
        )

        post.delete()

        messages.success(
            request,
            "Post deleted successfully."
        )

    return redirect("accounts:account_detail")


# -------------------------
# LOGOUT
# -------------------------
@login_required
@never_cache
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

    # The ID now refers to a Community Post
    post = get_object_or_404(Post, id=moment_id)

    like = PostLike.objects.filter(
        post=post,
        user=request.user
    )

    if like.exists():
        like.delete()
        liked = False
    else:
        PostLike.objects.create(
            post=post,
            user=request.user
        )
        liked = True

    return JsonResponse({
        "liked": liked,
        "total_likes": post.likes.count()
    })
