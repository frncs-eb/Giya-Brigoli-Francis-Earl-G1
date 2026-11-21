from django.urls import path
from . import views

app_name = 'schedule'
urlpatterns = [
    path('', views.calendar, name='calendar'),
    path('new/', views.class_create, name='class_create'),
    path('<int:pk>/edit/', views.class_edit, name='class_edit'),
    path('<int:pk>/delete/', views.class_delete, name='class_delete'),
]
