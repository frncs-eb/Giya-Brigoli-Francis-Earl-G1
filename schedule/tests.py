from datetime import date, time, timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from .forms import ClassScheduleForm
from .models import ClassSchedule

User = get_user_model()


class ClassScheduleValidationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='student', password='pass12345')

    def make(self, **kwargs):
        data = {'user': self.user, 'subject_name': 'Math', 'day_of_week': 1, 'start_time': time(9), 'end_time': time(10)}
        data.update(kwargs)
        return ClassSchedule(**data)

    def test_invalid_day_and_end_time_constraints(self):
        for day in (0, 8):
            obj = self.make(day_of_week=day)
            with self.assertRaises(ValidationError):
                obj.full_clean()
            with self.assertRaises(IntegrityError), transaction.atomic():
                obj.save()
        obj = self.make(end_time=time(9))
        with self.assertRaises(ValidationError):
            obj.full_clean()
        with self.assertRaises(IntegrityError), transaction.atomic():
            obj.save()

    def test_unique_start_and_overlaps_rejected_adjacent_allowed(self):
        first = self.make()
        first.save()
        duplicate = self.make(subject_name='Duplicate')
        with self.assertRaises(IntegrityError), transaction.atomic():
            duplicate.save()
        overlap = self.make(start_time=time(9, 30), end_time=time(10, 30))
        with self.assertRaises(ValidationError):
            overlap.full_clean()
        adjacent = self.make(start_time=time(10), end_time=time(11))
        adjacent.full_clean()
        adjacent.save()

    def test_form_reports_overlap(self):
        ClassSchedule.objects.create(user=self.user, subject_name='Math', day_of_week=1, start_time=time(9), end_time=time(10))
        form = ClassScheduleForm(data={'subject_name': 'Physics', 'day_of_week': 1, 'start_time': '09:30', 'end_time': '10:30', 'room': ''}, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('overlaps', str(form.errors))


class ScheduleViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='owner', password='pass12345')
        self.other = User.objects.create_user(username='other', password='pass12345')
        self.obj = ClassSchedule.objects.create(user=self.user, subject_name='Biology', day_of_week=2, start_time=time(10), end_time=time(11))

    def test_authentication_and_ownership(self):
        self.assertRedirects(self.client.get(reverse('schedule:calendar')), f"{reverse('accounts:login')}?next={reverse('schedule:calendar')}")
        self.client.force_login(self.other)
        for url in (reverse('schedule:class_edit', args=[self.obj.pk]), reverse('schedule:class_delete', args=[self.obj.pk])):
            response = self.client.post(url, {'view': 'week', 'date': date.today().isoformat()})
            self.assertEqual(response.status_code, 404)
        self.assertEqual(self.client.get(reverse('schedule:class_edit', args=[self.obj.pk])).status_code, 404)

    def test_delete_requires_post(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse('schedule:class_delete', args=[self.obj.pk])).status_code, 405)

    def test_calendar_views_filter_users_and_invalid_date(self):
        self.client.force_login(self.user)
        ClassSchedule.objects.create(user=self.other, subject_name='Secret', day_of_week=2, start_time=time(12), end_time=time(13))
        for view in ('week', 'month'):
            response = self.client.get(reverse('schedule:calendar'), {'view': view, 'date': '2026-11-21'})
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'Biology')
            self.assertNotContains(response, 'Secret')
        response = self.client.get(reverse('schedule:calendar'), {'date': 'not-a-date'})
        self.assertEqual(response.status_code, 200)

