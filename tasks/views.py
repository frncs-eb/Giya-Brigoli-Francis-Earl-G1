from collections import OrderedDict
from datetime import datetime, time, timedelta
from hashlib import sha256

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import QuickTaskForm, TaskForm
from .models import Task

try:
    from schedule.models import ClassSchedule
except ImportError:
    ClassSchedule = None


def course_suggestions(user):
    courses = set(
        Task.objects.filter(user=user)
        .values_list("course", flat=True)
        .distinct()
    )
    if ClassSchedule is not None:
        courses.update(
            ClassSchedule.objects.filter(user=user)
            .values_list("subject_name", flat=True)
            .distinct()
        )
    return sorted(course.strip() for course in courses if course and course.strip())


def course_hue(course):
    return int.from_bytes(sha256(course.casefold().encode("utf-8")).digest()[:2], "big") % 360


def safe_next(request, fallback):
    candidate = request.POST.get("next", "")
    if candidate and url_has_allowed_host_and_scheme(
        candidate,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return candidate
    return fallback


def home_context(request, quick_form=None):
    user_tasks = Task.objects.filter(user=request.user)
    now = timezone.now()
    today = timezone.localdate()
    week_end_date = today + timedelta(days=6 - today.weekday())
    week_end = timezone.make_aware(
        datetime.combine(week_end_date, time.max),
        timezone.get_current_timezone(),
    )
    pending = Q(status__in=[Task.Status.NOT_STARTED, Task.Status.IN_PROGRESS])
    summary = user_tasks.aggregate(
        total=Count("pk"),
        pending=Count("pk", filter=pending),
        overdue=Count("pk", filter=pending & Q(due_date__lt=now)),
        due_this_week=Count(
            "pk",
            filter=pending & Q(due_date__gte=now, due_date__lte=week_end),
        ),
        completed=Count("pk", filter=Q(status=Task.Status.DONE)),
    )

    selected_course = request.GET.get("course", "")
    selected_status = request.GET.get("status", "")
    selected_priority = request.GET.get("priority", "")
    search = request.GET.get("q", "").strip()
    sort = request.GET.get("sort", "deadline")
    if sort not in {"deadline", "course", "status"}:
        sort = "deadline"

    tasks = user_tasks
    if selected_course:
        tasks = tasks.filter(course=selected_course)
    if selected_status in Task.Status.values:
        tasks = tasks.filter(status=selected_status)
    else:
        selected_status = ""
    if selected_priority in Task.Priority.values:
        tasks = tasks.filter(priority=selected_priority)
    else:
        selected_priority = ""
    if search:
        tasks = tasks.filter(Q(title__icontains=search) | Q(course__icontains=search))

    group_by_course = request.GET.get("group_by_course") in {"1", "true", "on"}
    ordering = {"deadline": "due_date", "course": "course", "status": "status"}[sort]
    if group_by_course and request.GET.get("view", "table") == "table":
        tasks = tasks.order_by("course", ordering, "title")
    else:
        tasks = tasks.order_by(ordering, "title")
    task_list = list(tasks)
    for task in task_list:
        task.course_hue = course_hue(task.course)

    grouped_tasks = []
    if group_by_course and request.GET.get("view", "table") == "table":
        groups = OrderedDict()
        for task in task_list:
            groups.setdefault(task.course, []).append(task)
        grouped_tasks = [
            {"course": course, "hue": course_hue(course), "tasks": items, "count": len(items)}
            for course, items in groups.items()
        ]

    view = request.GET.get("view", "table")
    if view not in {"table", "board"}:
        view = "table"
    params = request.GET.copy()
    params["view"] = "table"
    table_url = f"{reverse('tasks:home')}?{params.urlencode()}"
    params["view"] = "board"
    board_url = f"{reverse('tasks:home')}?{params.urlencode()}"
    current_url = request.get_full_path()

    return {
        "tasks": task_list,
        "grouped_tasks": grouped_tasks,
        "group_by_course": group_by_course,
        "summary": summary,
        "view": view,
        "table_url": table_url,
        "board_url": board_url,
        "current_url": current_url,
        "courses": sorted(user_tasks.values_list("course", flat=True).distinct()),
        "course_suggestions": course_suggestions(request.user),
        "statuses": Task.Status.choices,
        "priorities": Task.Priority.choices,
        "selected_course": selected_course,
        "selected_status": selected_status,
        "selected_priority": selected_priority,
        "search": search,
        "sort": sort,
        "quick_form": quick_form or QuickTaskForm(course_suggestions=course_suggestions(request.user)),
        "status_columns": Task.Status.choices,
    }


@login_required
def home(request):
    return render(request, "tasks/home.html", home_context(request))


@login_required
@require_POST
def create(request):
    suggestions = course_suggestions(request.user)
    form = QuickTaskForm(request.POST, course_suggestions=suggestions)
    if form.is_valid():
        Task.objects.create(
            user=request.user,
            course=form.cleaned_data["course"],
            title=form.cleaned_data["title"],
            due_date=form.cleaned_data["due_date"],
        )
        messages.success(request, "Task added.")
        return redirect(safe_next(request, reverse("tasks:home")))
    messages.error(request, "Please correct the task details below.")
    return render(
        request,
        "tasks/home.html",
        home_context(request, quick_form=form),
        status=400,
    )


@login_required
def edit(request, pk):
    task = get_object_or_404(Task, pk=pk, user=request.user)
    suggestions = course_suggestions(request.user)
    if request.method == "POST":
        form = TaskForm(request.POST, instance=task, course_suggestions=suggestions)
        if form.is_valid():
            form.save()
            messages.success(request, "Task updated.")
            return redirect(safe_next(request, reverse("tasks:home")))
        messages.error(request, "Please correct the task details below.")
    else:
        form = TaskForm(instance=task, course_suggestions=suggestions)
    return render(
        request,
        "tasks/edit.html",
        {"form": form, "task": task, "course_suggestions": suggestions, "next": request.GET.get("next", "")},
    )


@login_required
def delete_confirm(request, pk):
    task = get_object_or_404(Task, pk=pk, user=request.user)
    return render(
        request,
        "tasks/delete_confirm.html",
        {"task": task, "next": request.GET.get("next", "")},
    )


@login_required
@require_POST
def delete(request, pk):
    task = get_object_or_404(Task, pk=pk, user=request.user)
    task.delete()
    messages.success(request, "Task deleted.")
    return redirect(safe_next(request, reverse("tasks:home")))


@login_required
@require_POST
def set_status(request, pk):
    task = get_object_or_404(Task, pk=pk, user=request.user)
    status = request.POST.get("status", "")
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    if status not in Task.Status.values:
        if is_ajax:
            return JsonResponse({"error": "Choose a valid task status."}, status=400)
        messages.error(request, "Choose a valid task status.")
        return redirect(safe_next(request, reverse("tasks:home")))
    task.status = status
    task.save(update_fields=["status", "completed_at"])
    if is_ajax:
        return JsonResponse({"status": task.status, "status_display": task.get_status_display()})
    messages.success(request, "Task status updated.")
    return redirect(safe_next(request, reverse("tasks:home")))
