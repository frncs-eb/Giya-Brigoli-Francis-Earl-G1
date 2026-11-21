from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q


class ClassSchedule(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    subject_name = models.CharField(max_length=100)
    room = models.CharField(max_length=50, blank=True, null=True)
    day_of_week = models.SmallIntegerField()
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        ordering = ['day_of_week', 'start_time']
        constraints = [
            models.CheckConstraint(condition=Q(day_of_week__gte=1, day_of_week__lte=7), name='schedule_day_1_to_7'),
            models.CheckConstraint(condition=Q(end_time__gt=F('start_time')), name='schedule_end_after_start'),
            models.UniqueConstraint(fields=['user', 'day_of_week', 'start_time'], name='schedule_unique_user_day_start'),
        ]

    def clean(self):
        super().clean()
        errors = {}
        if self.start_time and self.end_time and self.end_time <= self.start_time:
            errors['end_time'] = 'End time must be later than start time.'
        if self.day_of_week and self.start_time and self.end_time and self.user_id and self.end_time > self.start_time:
            conflicts = ClassSchedule.objects.filter(
                user_id=self.user_id, day_of_week=self.day_of_week,
                start_time__lt=self.end_time, end_time__gt=self.start_time,
            )
            if self.pk:
                conflicts = conflicts.exclude(pk=self.pk)
            if conflicts.exists():
                errors['start_time'] = 'This class overlaps another class on the same day.'
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f'{self.subject_name} — {self.get_day_of_week_display() if hasattr(self, "get_day_of_week_display") else self.day_of_week}'

    def get_day_of_week_display(self):
        return dict(self.DAY_CHOICES).get(self.day_of_week, self.day_of_week)

    DAY_CHOICES = [(1, 'Monday'), (2, 'Tuesday'), (3, 'Wednesday'), (4, 'Thursday'), (5, 'Friday'), (6, 'Saturday'), (7, 'Sunday')]
