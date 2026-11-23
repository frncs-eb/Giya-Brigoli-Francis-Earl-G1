from django.urls import path

from . import views

app_name = 'clinical'

urlpatterns = [
    path('', views.home, name='home'),
]
