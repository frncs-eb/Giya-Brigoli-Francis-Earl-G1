from django.contrib import admin
from .models import ClassSchedule


@admin.register(ClassSchedule)
class ClassScheduleAdmin(admin.ModelAdmin):
    list_display = ('subject_name', 'user', 'day_of_week', 'start_time', 'end_time', 'room')
    list_filter = ('day_of_week',)
