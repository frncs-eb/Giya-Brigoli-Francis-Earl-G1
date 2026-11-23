from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from .suggestions import CASES_BY_AREA


class ClinicalLog(models.Model):
    class Area(models.TextChoices):
        OR = 'OR', 'OR'
        DR = 'DR', 'DR'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='clinical_logs')
    hospital = models.CharField(max_length=100)
    duty_date = models.DateField()
    duty_time = models.TimeField()
    area = models.CharField(max_length=2, choices=Area.choices)
    case_type = models.CharField(max_length=100)

    class Meta:
        ordering = ['-duty_date', '-duty_time']

    def clean(self):
        super().clean()
        if self.area and self.case_type and self.case_type not in CASES_BY_AREA.get(self.area, ()):
            raise ValidationError({'case_type': 'Choose a case that matches OR or DR.'})

    def __str__(self):
        return f'{self.hospital} — {self.get_area_display()} — {self.duty_date}'
