from datetime import timedelta
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Task


class TaskModelTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="task-user", password="pass")

    def make_task(self, **kwargs):
        defaults = {
            "user": self.user,
            "course": "Nursing",
            "title": "Quiz 2",
            "due_date": timezone.now() + timedelta(days=5),
        }
        defaults.update(kwargs)
        return Task.objects.create(**defaults)

    def test_invalid_status_and_priority_are_rejected(self):
        for field, value in (("status", "INVALID"), ("priority", "URGENT")):
            task = Task(
                user=self.user,
                course="Nursing",
                title="Quiz",
                due_date=timezone.now(),
                **{field: value},
            )
            with self.subTest(field=field):
                with self.assertRaises(ValidationError):
                    task.full_clean()
                with self.assertRaises(IntegrityError):
                    with transaction.atomic():
                        Task.objects.create(
                            user=self.user,
                            course="Nursing",
                            title="Bad value",
                            due_date=timezone.now(),
                            **{field: value},
                        )

    def test_completed_at_is_set_and_cleared_when_reopened(self):
        task = self.make_task()
        task.status = Task.Status.DONE
        task.save(update_fields=["status"])
        task.refresh_from_db()
        self.assertIsNotNone(task.completed_at)
        task.status = Task.Status.IN_PROGRESS
        task.save(update_fields=["status"])
        task.refresh_from_db()
        self.assertIsNone(task.completed_at)

    def test_done_without_completed_at_violates_constraint(self):
        task = self.make_task()
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Task.objects.filter(pk=task.pk).update(status=Task.Status.DONE, completed_at=None)

    def test_due_properties_cover_past_soon_far_and_done(self):
        past = self.make_task(title="Past", due_date=timezone.now() - timedelta(hours=1))
        soon = self.make_task(title="Soon", due_date=timezone.now() + timedelta(hours=24))
        far = self.make_task(title="Far", due_date=timezone.now() + timedelta(days=5))
        done = self.make_task(title="Done", due_date=timezone.now() - timedelta(hours=1), status=Task.Status.DONE)
        self.assertTrue(past.is_overdue)
        self.assertFalse(past.is_due_soon)
        self.assertTrue(soon.is_due_soon)
        self.assertFalse(soon.is_overdue)
        self.assertFalse(far.is_due_soon)
        self.assertFalse(far.is_overdue)
        self.assertFalse(done.is_due_soon)
        self.assertFalse(done.is_overdue)


class TaskViewTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="owner", password="pass")
        self.other = User.objects.create_user(username="other", password="pass")

    def make_task(self, user=None, **kwargs):
        values = {
            "user": user or self.user,
            "course": "Pharmacology",
            "title": "Case study",
            "due_date": timezone.now() + timedelta(days=3),
        }
        values.update(kwargs)
        return Task.objects.create(**values)

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(reverse("tasks:home"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)

    def test_mutating_endpoints_reject_get(self):
        self.client.login(username="owner", password="pass")
        task = self.make_task()
        self.assertEqual(self.client.get(reverse("tasks:create")).status_code, 405)
        self.assertEqual(self.client.get(reverse("tasks:set_status", args=[task.pk])).status_code, 405)
        self.assertEqual(self.client.get(reverse("tasks:delete", args=[task.pk])).status_code, 405)
        self.assertEqual(self.client.get(reverse("tasks:delete_confirm", args=[task.pk])).status_code, 200)

    def test_another_users_task_is_hidden_from_view_edit_delete_and_status(self):
        self.client.login(username="owner", password="pass")
        task = self.make_task(user=self.other)
        self.assertEqual(self.client.get(reverse("tasks:edit", args=[task.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("tasks:delete_confirm", args=[task.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("tasks:delete", args=[task.pk])).status_code, 404)
        self.assertEqual(
            self.client.post(reverse("tasks:set_status", args=[task.pk]), {"status": Task.Status.DONE}).status_code,
            404,
        )
        response = self.client.get(reverse("tasks:home"))
        self.assertNotContains(response, "Case study")

    def test_create_delete_and_status_change(self):
        self.client.login(username="owner", password="pass")
        create_response = self.client.post(
            reverse("tasks:create"),
            {"course": "  Pharmacology ", "title": "  Quiz 2  ", "due_date": (timezone.now() + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M")},
        )
        self.assertEqual(create_response.status_code, 302)
        task = Task.objects.get(user=self.user)
        self.assertEqual(task.course, "Pharmacology")
        self.assertEqual(task.title, "Quiz 2")

        ajax_response = self.client.post(
            reverse("tasks:set_status", args=[task.pk]),
            {"status": Task.Status.DONE},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(ajax_response.status_code, 200)
        self.assertEqual(ajax_response.json()["status_display"], "Done")
        task.refresh_from_db()
        self.assertIsNotNone(task.completed_at)

        redirect_response = self.client.post(
            reverse("tasks:set_status", args=[task.pk]),
            {"status": Task.Status.IN_PROGRESS, "next": "/tasks/?view=board"},
        )
        self.assertRedirects(redirect_response, "/tasks/?view=board", fetch_redirect_response=False)
        task.refresh_from_db()
        self.assertIsNone(task.completed_at)

        delete_response = self.client.post(reverse("tasks:delete", args=[task.pk]))
        self.assertEqual(delete_response.status_code, 302)
        self.assertFalse(Task.objects.filter(pk=task.pk).exists())

    def test_filters_search_sort_and_summary_are_user_scoped(self):
        now = timezone.now()
        late = self.make_task(title="Late lab", course="Biology", due_date=now - timedelta(days=1))
        soon = self.make_task(title="Upcoming quiz", due_date=now + timedelta(hours=20))
        completed = self.make_task(title="Finished report", status=Task.Status.DONE, due_date=now + timedelta(days=1))
        self.make_task(user=self.other, title="Secret assignment", course="Biology")

        self.client.login(username="owner", password="pass")
        response = self.client.get(reverse("tasks:home"), {"course": "Biology", "q": "lab", "sort": "course"})
        self.assertContains(response, "Late lab")
        self.assertNotContains(response, "Upcoming quiz")
        self.assertNotContains(response, "Secret assignment")
        self.assertEqual(response.context["summary"]["total"], 3)
        self.assertEqual(response.context["summary"]["pending"], 2)
        self.assertEqual(response.context["summary"]["overdue"], 1)
        self.assertEqual(response.context["summary"]["completed"], 1)
        self.assertEqual(response.context["summary"]["due_this_week"], 1)

    def test_empty_user_has_zero_summary(self):
        self.client.login(username="owner", password="pass")
        response = self.client.get(reverse("tasks:home"))
        self.assertEqual(response.context["summary"], {"total": 0, "pending": 0, "overdue": 0, "due_this_week": 0, "completed": 0})
        self.assertContains(response, "No tasks yet")

    def test_invalid_quick_add_renders_errors(self):
        self.client.login(username="owner", password="pass")
        response = self.client.post(reverse("tasks:create"), {"course": "  ", "title": "  ", "due_date": ""})
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Enter a course or subject.", status_code=400)

    def test_dashboard_overdue_only_does_not_claim_there_are_no_pending_tasks(self):
        self.make_task(title="Overdue only", due_date=timezone.now() - timedelta(hours=1))
        self.client.login(username="owner", password="pass")
        response = self.client.get(reverse("dashboard:home"))
        self.assertContains(response, "1 overdue")
        self.assertContains(response, "No upcoming deadlines")
        self.assertNotContains(response, "No pending tasks")

    def test_dashboard_tasks_card_with_and_without_tasks(self):
        self.client.login(username="owner", password="pass")
        response = self.client.get(reverse("dashboard:home"))
        self.assertContains(response, "Tasks")
        self.assertContains(response, "No pending tasks")
        task = self.make_task(due_date=timezone.now() - timedelta(hours=1))
        upcoming = self.make_task(title="Next task", due_date=timezone.now() + timedelta(days=2))
        response = self.client.get(reverse("dashboard:home"))
        self.assertContains(response, upcoming.title)
        self.assertContains(response, "1 overdue")
