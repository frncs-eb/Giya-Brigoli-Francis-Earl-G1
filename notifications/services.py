import logging
from datetime import datetime, time, timedelta
from decimal import Decimal
from django.apps import apps
from django.db.models import Sum
from django.utils import timezone
from .models import Notification, NotificationPreference

logger=logging.getLogger(__name__)

def generate_for_user(user, now=None):
    now=timezone.localtime(now or timezone.now()); today=now.date(); prefs,_=NotificationPreference.objects.get_or_create(user=user); made=0; data_present=False
    def add(category,level,title,message,key,link=''):
        nonlocal made
        if not getattr(prefs,category.lower(),True): return
        _,created=Notification.objects.get_or_create(user=user,dedupe_key=key,defaults={'category':category,'level':level,'title':title[:120],'message':message[:255],'link':link[:200]})
        made+=int(created)
    if apps.is_installed('budget'):
      try:
        from budget.models import BudgetAllowance
        allowances=BudgetAllowance.objects.filter(user=user); active=allowances.filter(start_date__lte=today,end_date__gte=today).annotate(spent=Sum('expenses__amount')).order_by('-start_date')
        data_present |= allowances.exists(); allowance=active.first()
        if allowance:
          spent=allowance.spent or Decimal('0'); pct=spent*100/allowance.amount
          link=__import__('django.urls',fromlist=['reverse']).reverse('budget:home')
          if pct>=80: add('BUDGET','WARNING',"You've used 80% of your allowance",f'You have spent ₱{spent} of ₱{allowance.amount}.',f'budget:{allowance.pk}:80',link)
          if pct>100: add('BUDGET','DANGER',f'Over budget by ₱{spent-allowance.amount:.2f}',f'You have spent ₱{spent} of ₱{allowance.amount}.',f'budget:{allowance.pk}:100',link)
          if (allowance.end_date-today).days<=2: add('BUDGET','INFO','Allowance ending soon',f'Your allowance ends on {allowance.end_date}.',f'budget:{allowance.pk}:ending',link)
        elif allowances.exists():
          from django.urls import reverse
          add('BUDGET','INFO','Set a new allowance','Your previous allowance has ended.',f'budget:none:{today:%Y-%m}',reverse('budget:home'))
      except Exception: logger.exception('Budget reminder source failed for user %s',user.pk)
    if apps.is_installed('schedule'):
      try:
        from schedule.models import ClassSchedule
        qs=ClassSchedule.objects.filter(user=user,day_of_week=today.isoweekday()); data_present |= ClassSchedule.objects.filter(user=user).exists()
        for c in qs:
          start=timezone.make_aware(datetime.combine(today,c.start_time),timezone.get_current_timezone())
          if now<=start<=now+timedelta(minutes=prefs.class_lead_minutes):
            from django.urls import reverse
            add('SCHEDULE','INFO',f'Class starting soon: {c.subject_name} at {c.start_time:%I:%M %p}, {c.room or ""}',f'{c.subject_name} starts at {c.start_time:%I:%M %p}.',f'class:{c.pk}:{today}',reverse('schedule:calendar'))
      except Exception: logger.exception('Schedule reminder source failed for user %s',user.pk)
    if apps.is_installed('tasks'):
      try:
        from tasks.models import Task
        tasks=Task.objects.filter(user=user).exclude(status='DONE'); data_present |= Task.objects.filter(user=user).exists()
        for t in tasks:
          delta=t.due_date-now
          from django.urls import reverse
          link=reverse('tasks:home')
          if delta.total_seconds()<0: add('TASK','DANGER',f'Overdue: {t.title} ({t.course})',f'{t.title} for {t.course} is overdue.',f'task:{t.pk}:overdue',link)
          elif delta<=timedelta(hours=3): add('TASK','DANGER',f'Due soon: {t.title}',f'{t.title} for {t.course} is due within 3 hours.',f'task:{t.pk}:urgent',link)
          elif delta<=timedelta(hours=48): add('TASK','WARNING',f'Task due soon: {t.title}',f'{t.title} for {t.course} is due within 48 hours.',f'task:{t.pk}:soon',link)
      except Exception: logger.exception('Task reminder source failed for user %s',user.pk)
    if apps.is_installed('clinical'):
      try:
        from clinical.models import ClinicalLog
        qs=ClinicalLog.objects.filter(user=user); data_present |= qs.exists()
        for d in qs.filter(duty_date__lte=today+timedelta(days=1)):
          from django.urls import reverse
          link=reverse('clinical:home')
          if d.duty_date<today: add('CLINICAL','WARNING',f'Update duty at {d.hospital}',f'Update the status and hours of your duty at {d.hospital}.',f'duty:{d.pk}:update',link)
          else: add('CLINICAL','INFO',f'Duty scheduled at {d.hospital}',f'Your duty at {d.hospital} is on {d.duty_date}.',f'duty:{d.pk}:{d.duty_date}',link)
      except Exception: logger.exception('Clinical reminder source failed for user %s',user.pk)
    if not data_present: add('SYSTEM','INFO','Welcome to Giya','Start by adding your class schedule or a budget allowance','system:welcome')
    Notification.objects.filter(user=user,is_read=True,created_at__lt=now-timedelta(days=30)).delete()
    stale=list(Notification.objects.filter(user=user).order_by('-created_at').values_list('pk',flat=True)[100:])
    if stale: Notification.objects.filter(pk__in=stale,user=user).delete()
    return made
