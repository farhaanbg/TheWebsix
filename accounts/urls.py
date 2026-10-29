from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views
from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("signup/", views.signup, name="signup"),

    # Account dashboard
    path("details/", views.dashboard_view, name="account_detail"),
    path("dashboard/", views.dashboard_view, name="dashboard"),

    # Account management
    path("edit/", views.edit_account, name="edit_account"),
    path("logout/", views.logout_view, name="logout"),
    path("delete/", views.delete_account, name="delete_account"),

    # Password change
    path(
        "password_change/",
        views.change_password,
        name="password_change"
    ),
    path(
        "password_change/done/",
        views.CustomPasswordChangeDoneView.as_view(),
        name="password_change_done"
    ),

    # Moments & Comments
    path(
        "moment/<int:moment_id>/delete/",
        views.delete_moment,
        name="delete_moment"
    ),
    path(
        "moment/<int:moment_id>/comments/",
        views.get_comments,
        name="get_comments"
    ),
    path(
        "moment/<int:moment_id>/comment/add/",
        views.add_comment,
        name="add_comment"
    ),
    path(
        "comment/<int:comment_id>/delete/",
        views.delete_comment,
        name="delete_comment"
    ),

    # Password reset
    
    path(
        'password_reset/',
        auth_views.PasswordResetView.as_view(
            template_name='registration/password_reset.html',
            email_template_name='accounts/password_reset_email.html',
            subject_template_name='accounts/password_reset_subject.txt',
            success_url='/accounts/password_reset/done/',
        ),
        name='password_reset',
    ),

    path(
        'password_reset/done/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='registration/password_reset_done.html',
        ),
        name='password_reset_done',
    ),

    path(
        'reset/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='registration/password_reset_confirm.html',
            success_url='/accounts/reset/done/',
        ),
        name='password_reset_confirm',
    ),

    path(
        'reset/done/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='registration/password_reset_complete.html',
        ),
        name='password_reset_complete',
    ),


    path(
        'toggle-like/<int:moment_id>/',
        views.toggle_like,
        name='toggle_like'
    ),
    
]

