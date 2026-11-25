from django.contrib import admin

from .models import Task


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "user", "status", "priority", "due_date")
    list_filter = ("status", "priority", "course")
    search_fields = ("title", "course", "user__username", "user__email")
    ordering = ("due_date",)
