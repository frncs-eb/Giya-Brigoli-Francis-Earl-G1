from django.urls import path

from . import views

app_name = 'budget'

urlpatterns = [
    path('', views.home, name='home'),
    path('allowances/add/', views.allowance_create, name='allowance_create'),
    path('allowances/<int:pk>/', views.allowance_detail, name='allowance_detail'),
    path('allowances/<int:pk>/edit/', views.allowance_edit, name='allowance_edit'),
    path('allowances/<int:pk>/delete/', views.allowance_delete, name='allowance_delete'),
    path('expenses/add/', views.expense_create, name='expense_create'),
    path('expenses/<int:pk>/edit/', views.expense_edit, name='expense_edit'),
    path('expenses/<int:pk>/delete/', views.expense_delete, name='expense_delete'),
]
