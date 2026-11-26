from django.contrib import admin
from .models import Notification, NotificationPreference

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'category', 'level', 'is_read', 'created_at')
    list_filter = ('category', 'level', 'is_read', 'created_at')
    search_fields = ('title', 'message', 'user__username', 'user__email')
    readonly_fields = ('created_at',)

@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ('user', 'budget', 'schedule', 'task', 'clinical', 'system', 'class_lead_minutes')
    list_filter = ('budget', 'schedule', 'task', 'clinical', 'system')
    search_fields = ('user__username', 'user__email')
