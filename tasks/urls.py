from django.urls import path

from . import views

app_name = "tasks"

urlpatterns = [
    path("", views.home, name="home"),
    path("create/", views.create, name="create"),
    path("<int:pk>/edit/", views.edit, name="edit"),
    path("<int:pk>/delete/confirm/", views.delete_confirm, name="delete_confirm"),
    path("<int:pk>/delete/", views.delete, name="delete"),
    path("<int:pk>/status/", views.set_status, name="set_status"),
]
