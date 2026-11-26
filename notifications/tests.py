from datetime import timedelta
from unittest import skipUnless
from django.apps import apps
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone
from .models import Notification, NotificationPreference
from .services import generate_for_user

class NotificationViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='notify', password='pass12345')
        self.other = get_user_model().objects.create_user(username='other', password='pass12345')
        self.client.login(username='notify', password='pass12345')
        self.note = Notification.objects.create(user=self.other, category='SYSTEM', level='INFO', title='Private', message='secret', dedupe_key='private')
    def test_login_and_owner_checks(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse('notifications:list')).status_code, 302)
        self.client.login(username='notify', password='pass12345')
        for name, method in [('notifications:open','get'), ('notifications:mark_read','post'), ('notifications:delete','post')]:
            response = getattr(self.client, method)(reverse(name, args=[self.note.pk]))
            self.assertEqual(response.status_code, 404)
    def test_mutations_post_only_and_poll(self):
        for name in ('notifications:mark_all_read','notifications:clear_read'):
            self.assertEqual(self.client.get(reverse(name)).status_code, 405)
        data = self.client.get(reverse('notifications:poll')).json()
        self.assertEqual(data, {'unread': 0, 'latest': []})
    def test_list_and_preferences(self):
        own = Notification.objects.create(user=self.user, category='SYSTEM', level='INFO', title='Own', message='hello', dedupe_key='own')
        self.assertContains(self.client.get(reverse('notifications:list')), 'Own')
        self.assertContains(self.client.get(reverse('notifications:preferences')), 'class_lead_minutes')
        self.assertEqual(self.client.post(reverse('notifications:mark_read', args=[own.pk])).status_code, 302)

class EngineTests(TestCase):
    def setUp(self): self.user = get_user_model().objects.create_user(username='engine')
    def test_idempotency_and_cleanup(self):
        generate_for_user(self.user); before=Notification.objects.filter(user=self.user).count(); generate_for_user(self.user)
        self.assertEqual(Notification.objects.filter(user=self.user).count(), before)
        Notification.objects.create(user=self.user,category='SYSTEM',level='INFO',title='Old',message='old',dedupe_key='old',is_read=True,created_at=timezone.now()-timedelta(days=31))
        for i in range(105): Notification.objects.create(user=self.user,category='SYSTEM',level='INFO',title=str(i),message='x',dedupe_key=f'k{i}')
        generate_for_user(self.user)
        self.assertLessEqual(Notification.objects.filter(user=self.user).count(),100)
        self.assertFalse(Notification.objects.filter(user=self.user,dedupe_key='old').exists())
    def test_context_processor_throttle(self):
        from .context_processors import notifications_context
        from unittest.mock import patch
        request=type('Request',(),{'user':self.user,'session':{}})()
        with patch('notifications.context_processors.generate_for_user') as gen:
            notifications_context(request); notifications_context(request)
            self.assertEqual(gen.call_count,1)

    def test_command_runs(self):
        call_command('send_reminders', stdout=None)

class DashboardReminderTests(TestCase):
    def setUp(self):
        self.user=get_user_model().objects.create_user(username='dashboard',password='pass12345')
        self.client.login(username='dashboard',password='pass12345')
    def test_dashboard_reminder_card_empty_and_populated(self):
        from unittest.mock import patch
        with patch('notifications.context_processors.generate_for_user'):
            response=self.client.get(reverse('dashboard:home'))
            self.assertContains(response,"You're all caught up")
            Notification.objects.create(user=self.user,category='SYSTEM',level='INFO',title='A reminder',message='Test',dedupe_key='dash')
            response=self.client.get(reverse('dashboard:home'))
        self.assertContains(response,'Reminders')
        self.assertContains(response,'A reminder')

@skipUnless(apps.is_installed('tasks'), 'tasks app is not installed')
class TaskReminderTests(TestCase):
    def test_task_due_reminders_and_done_skip(self):
        from tasks.models import Task
        user=get_user_model().objects.create_user(username='tasks')
        now=timezone.now()
        for title,delta,status in [('soon',timedelta(hours=20),'NOT_STARTED'),('urgent',timedelta(hours=2),'IN_PROGRESS'),('late',-timedelta(hours=1),'NOT_STARTED'),('done',timedelta(hours=1),'DONE')]:
            Task.objects.create(user=user,course='Course',title=title,due_date=now+delta,status=status)
        generate_for_user(user,now)
        keys=set(Notification.objects.filter(user=user,category='TASK').values_list('dedupe_key',flat=True))
        self.assertEqual(keys,{'task:1:soon','task:2:urgent','task:3:overdue'})

@skipUnless(apps.is_installed('budget'), 'budget app is not installed')
class BudgetReminderTests(TestCase):
    def test_eighty_and_over_budget(self):
        from budget.models import BudgetAllowance, Expense, ExpenseCategory
        user=get_user_model().objects.create_user(username='budget-test')
        today=timezone.localdate()
        allowance=BudgetAllowance.objects.create(user=user,amount='100',period_type='MONTHLY',start_date=today,end_date=today+timedelta(days=10))
        category=ExpenseCategory.objects.create(name='Test')
        Expense.objects.create(allowance=allowance,category=category,item_name='80%',amount='80',expense_date=today)
        generate_for_user(user)
        self.assertTrue(Notification.objects.filter(user=user,dedupe_key=f'budget:{allowance.pk}:80').exists())
        Expense.objects.create(allowance=allowance,category=category,item_name='over',amount='30',expense_date=today)
        generate_for_user(user)
        self.assertTrue(Notification.objects.filter(user=user,dedupe_key=f'budget:{allowance.pk}:100',level='DANGER').exists())

@skipUnless(apps.is_installed('schedule'), 'schedule app is not installed')
class ScheduleReminderTests(TestCase):
    def test_upcoming_and_started_classes(self):
        from schedule.models import ClassSchedule
        user=get_user_model().objects.create_user(username='schedule-test')
        now=timezone.localtime(); lead=now+timedelta(minutes=30); started=now-timedelta(minutes=5)
        ClassSchedule.objects.create(user=user,subject_name='Soon',day_of_week=now.isoweekday(),start_time=lead.time().replace(second=0,microsecond=0),end_time=(lead+timedelta(hours=1)).time().replace(second=0,microsecond=0))
        ClassSchedule.objects.create(user=user,subject_name='Started',day_of_week=now.isoweekday(),start_time=started.time().replace(second=0,microsecond=0),end_time=(now+timedelta(hours=1)).time().replace(second=0,microsecond=0))
        generate_for_user(user,now)
        rows=Notification.objects.filter(user=user,category='SCHEDULE')
        self.assertEqual(rows.count(),1)
        self.assertIn('Soon',rows.first().title)

@skipUnless(apps.is_installed('clinical'), 'clinical app is not installed')
class ClinicalReminderTests(TestCase):
    def test_tomorrow_and_stale_duties(self):
        from clinical.models import ClinicalLog
        user=get_user_model().objects.create_user(username='clinical-test')
        today=timezone.localdate()
        ClinicalLog.objects.create(user=user,hospital='Tomorrow Site',duty_date=today+timedelta(days=1),duty_time='08:00',area='OR',case_type='General surgery')
        ClinicalLog.objects.create(user=user,hospital='Past Site',duty_date=today-timedelta(days=1),duty_time='08:00',area='OR',case_type='General surgery')
        generate_for_user(user)
        self.assertTrue(Notification.objects.filter(user=user,category='CLINICAL',title__contains='Tomorrow Site').exists())
        self.assertTrue(Notification.objects.filter(user=user,category='CLINICAL',title__contains='Past Site',level='WARNING').exists())
