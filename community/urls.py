from django.urls import path
from . import views


app_name = 'community'

urlpatterns = [
    path('reviews/', views.ReviewListView.as_view(), name='reviews'),
    path('community/', views.PostListView.as_view(), name='community'),
    path('community/posts/<int:pk>/', views.PostDetailView.as_view(), name='post-detail'),

   
    path('reviews/create/', views.add_review, name='review_create'),
    path('community/posts/create/', views.add_post, name='post_create'),
    path('community/posts/<int:pk>/comments/', views.add_comment, name='comment_create'),
    path('community/posts/<int:pk>/like/', views.like_post, name='post_like'),
    path('community/posts/<int:pk>/delete/', views.delete_post, name='post_delete'),
    path('community/login/', views.CommunityLoginView.as_view(), name='login'),
]
