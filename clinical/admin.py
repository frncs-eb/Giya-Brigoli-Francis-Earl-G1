from django.contrib import admin

from .models import ClinicalLog


@admin.register(ClinicalLog)
class ClinicalLogAdmin(admin.ModelAdmin):
    list_display = ('duty_date', 'duty_time', 'hospital', 'area', 'case_type', 'user')
    list_filter = ('area', 'duty_date')
    search_fields = ('hospital', 'case_type', 'user__username')
