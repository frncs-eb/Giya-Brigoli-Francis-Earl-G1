from django.urls import path
from . import views

app_name = 'notifications'
urlpatterns = [
    path('', views.notification_list, name='list'),
    path('open/<int:pk>/', views.open_notification, name='open'),
    path('<int:pk>/read/', views.mark_read, name='mark_read'),
    path('read-all/', views.mark_all_read, name='mark_all_read'),
    path('<int:pk>/delete/', views.delete_notification, name='delete'),
    path('clear-read/', views.clear_read, name='clear_read'),
    path('preferences/', views.preferences, name='preferences'),
    path('poll/', views.poll, name='poll'),
]
