from django.urls import path
from . import views

app_name = 'hikes'
urlpatterns = [
    path('', views.hike_list, name='list'),
    path('<int:pk>/', views.hike_detail, name='detail'),
]
