from django.urls import path
from . import views

app_name = 'hikes'
urlpatterns = [
    path('saved/', views.saved_hikes, name='saved'),
    path('announcements/', views.announcements, name='announcements'),
    path('<int:pk>/save/', views.save_hike, name='save'),
    path('<int:pk>/unsave/', views.remove_saved_hike, name='unsave'),
    path('', views.hike_list, name='list'),
    path('<int:pk>/', views.hike_detail, name='detail'),
]
