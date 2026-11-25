from datetime import timedelta

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone


class Task(models.Model):
    class Priority(models.TextChoices):
        LOW = "LOW", "Low"
        MEDIUM = "MEDIUM", "Medium"
        HIGH = "HIGH", "High"

    class Status(models.TextChoices):
        NOT_STARTED = "NOT_STARTED", "Not started"
        IN_PROGRESS = "IN_PROGRESS", "In progress"
        DONE = "DONE", "Done"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    course = models.CharField(max_length=100)
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    due_date = models.DateTimeField()
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NOT_STARTED)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["due_date"]
        constraints = [
            models.CheckConstraint(
                condition=Q(status__in=["NOT_STARTED", "IN_PROGRESS", "DONE"]),
                name="task_status_valid",
            ),
            models.CheckConstraint(
                condition=Q(priority__in=["LOW", "MEDIUM", "HIGH"]),
                name="task_priority_valid",
            ),
            models.CheckConstraint(
                condition=(
                    Q(status="DONE", completed_at__isnull=False)
                    | (~Q(status="DONE") & Q(completed_at__isnull=True))
                ),
                name="task_completed_at_matches_status",
            ),
        ]

    def save(self, *args, **kwargs):
        if self.status == self.Status.DONE:
            if self.completed_at is None:
                self.completed_at = timezone.now()
        else:
            self.completed_at = None
        if kwargs.get("update_fields") is not None:
            kwargs["update_fields"] = set(kwargs["update_fields"]) | {"completed_at"}
        super().save(*args, **kwargs)

    @property
    def is_overdue(self):
        return self.status != self.Status.DONE and self.due_date < timezone.now()

    @property
    def is_due_soon(self):
        now = timezone.now()
        return self.status != self.Status.DONE and now <= self.due_date <= now + timedelta(hours=48)

    def __str__(self):
        return f"{self.course}: {self.title}"
