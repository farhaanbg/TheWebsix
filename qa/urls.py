from django.urls import path

from . import views

# Namespace: templates use {% url 'qa:list' %} instead of hard-coding /qa/.
app_name = 'qa'

urlpatterns = [
    path('', views.QuestionListView.as_view(), name='list'),               # /qa/
    path('ask/', views.ask_question, name='ask'),                          # /qa/ask/
    path('<int:pk>/delete/', views.delete_question, name='delete'),        # /qa/5/delete/
]
