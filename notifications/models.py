from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models

class Notification(models.Model):
    class Category(models.TextChoices):
        BUDGET='BUDGET','Budget'; SCHEDULE='SCHEDULE','Schedule'; TASK='TASK','Task'; CLINICAL='CLINICAL','Clinical'; SYSTEM='SYSTEM','System'
    class Level(models.TextChoices):
        INFO='INFO','Info'; WARNING='WARNING','Warning'; DANGER='DANGER','Danger'
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE)
    category=models.CharField(max_length=10,choices=Category.choices)
    level=models.CharField(max_length=10,choices=Level.choices)
    title=models.CharField(max_length=120); message=models.CharField(max_length=255)
    link=models.CharField(max_length=200,blank=True); dedupe_key=models.CharField(max_length=120)
    is_read=models.BooleanField(default=False); created_at=models.DateTimeField(auto_now_add=True); read_at=models.DateTimeField(null=True,blank=True)
    class Meta:
        ordering=('-created_at',)
        constraints=[models.UniqueConstraint(fields=('user','dedupe_key'),name='notification_user_dedupe_unique')]
        indexes=[models.Index(fields=('user','is_read'),name='notif_user_read_idx')]

class NotificationPreference(models.Model):
    user=models.OneToOneField(settings.AUTH_USER_MODEL,on_delete=models.CASCADE)
    budget=models.BooleanField(default=True); schedule=models.BooleanField(default=True); task=models.BooleanField(default=True); clinical=models.BooleanField(default=True); system=models.BooleanField(default=True)
    class_lead_minutes=models.PositiveSmallIntegerField(default=60,validators=[MinValueValidator(15),MaxValueValidator(180)])
