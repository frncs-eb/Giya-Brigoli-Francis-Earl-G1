import hashlib
import calendar as month_calendar
from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_http_methods, require_POST

from .forms import ClassScheduleForm
from .models import ClassSchedule

COLORS = ['#dceee4', '#e4e7f7', '#f7e8d5', '#f5dfe4', '#d9eef0', '#eee3f5', '#e9edcf', '#f6e6cf']
DAY_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']


def _calendar_url(view, current):
    return f"{reverse('schedule:calendar')}?view={view}&date={current.isoformat()}"


def _parse_date(raw):
    try:
        return parse_date(raw or '') or date.today()
    except ValueError:
        return date.today()


def _decorate(item):
    digest = hashlib.sha256(item.subject_name.casefold().encode()).hexdigest()
    item.color = COLORS[int(digest, 16) % len(COLORS)]
    start = item.start_time.hour * 60 + item.start_time.minute
    end = item.end_time.hour * 60 + item.end_time.minute
    item.top = max(0, (start - 360) * 64 / 60)
    item.height = max(24, (end - start) * 64 / 60)
    fmt = lambda value: f'{value.strftime("%I:%M %p").lstrip("0")}'
    item.time_label = f'{fmt(item.start_time)} – {fmt(item.end_time)}'
    return item


def _context(user, view, current, form=None, instance=None, modal_open=False):
    classes = list(ClassSchedule.objects.filter(user=user))
    by_day = {i: [] for i in range(1, 8)}
    for obj in classes:
        by_day[obj.day_of_week].append(_decorate(obj))
    monday = current - timedelta(days=current.weekday())
    if view == 'month':
        first = current.replace(day=1)
        weeks = month_calendar.Calendar(firstweekday=0).monthdatescalendar(current.year, current.month)
        month_days = [{'date': d, 'in_month': d.month == current.month, 'classes': by_day[d.isoweekday()]} for week in weeks for d in week]
        previous = (first - timedelta(days=1)).replace(day=1)
        following = (first.replace(day=28) + timedelta(days=4)).replace(day=1)
        title, days = current.strftime('%B %Y'), []
    else:
        sunday = monday + timedelta(days=6)
        title = f'{monday.strftime("%b")} {monday.day} – {sunday.day}, {sunday.year}' if monday.month == sunday.month else f'{monday.strftime("%b")} {monday.day} – {sunday.strftime("%b")} {sunday.day}, {sunday.year}'
        days = [{'date': monday + timedelta(days=i), 'classes': by_day[i + 1], 'today': monday + timedelta(days=i) == date.today()} for i in range(7)]
        previous, following = current - timedelta(days=7), current + timedelta(days=7)
        month_days = []
    return {
        'view': view, 'current': current, 'title': title, 'days': days, 'month_days': month_days,
        'previous_url': _calendar_url(view, previous), 'next_url': _calendar_url(view, following),
        'today_url': _calendar_url(view, date.today()), 'class_count': len(classes),
        'day_names': DAY_NAMES, 'form': form or ClassScheduleForm(user=user), 'modal_open': modal_open, 'today': date.today(),
        'editing': instance, 'form_action': reverse('schedule:class_edit', args=[instance.pk]) if instance else reverse('schedule:class_create'),
        'redirect_view': view, 'redirect_date': current.isoformat(), 'create_url': reverse('schedule:class_create'),
        'week_start': monday, 'hours': range(6, 22),
    }


@login_required
def calendar(request):
    view = request.GET.get('view', 'week')
    if view not in ('week', 'month'):
        view = 'week'
    current = _parse_date(request.GET.get('date'))
    return render(request, 'schedule/calendar.html', _context(request.user, view, current, modal_open=request.GET.get('modal') == '1'))


def _save_form(request, instance=None):
    view = request.POST.get('view', 'week')
    if view not in ('week', 'month'):
        view = 'week'
    current = _parse_date(request.POST.get('date'))
    form = ClassScheduleForm(request.POST, instance=instance, user=request.user)
    if form.is_valid():
        obj = form.save()
        messages.success(request, f'{obj.subject_name} saved to your schedule.')
        return redirect(_calendar_url(view, current))
    if request.POST.get('fallback'):
        return render(request, 'schedule/class_form.html', {'form': form, 'is_edit': bool(instance), 'object': instance, 'view': view, 'current': current}, status=400)
    return render(request, 'schedule/calendar.html', _context(request.user, view, current, form, instance, True), status=400)


@login_required
@require_http_methods(['GET', 'POST'])
def class_create(request):
    if request.method == 'POST':
        return _save_form(request)
    view = request.GET.get('view', 'week')
    return render(request, 'schedule/class_form.html', {'form': ClassScheduleForm(user=request.user), 'is_edit': False, 'view': view, 'current': _parse_date(request.GET.get('date'))})


@login_required
@require_http_methods(['GET', 'POST'])
def class_edit(request, pk):
    obj = get_object_or_404(ClassSchedule, pk=pk, user=request.user)
    if request.method == 'POST':
        return _save_form(request, obj)
    return render(request, 'schedule/class_form.html', {'form': ClassScheduleForm(instance=obj, user=request.user), 'is_edit': True, 'object': obj, 'view': request.GET.get('view', 'week'), 'current': _parse_date(request.GET.get('date'))})


@login_required
@require_POST
def class_delete(request, pk):
    obj = get_object_or_404(ClassSchedule, pk=pk, user=request.user)
    name = obj.subject_name
    obj.delete()
    messages.success(request, f'{name} deleted from your schedule.')
    view = request.POST.get('view', 'week')
    if view not in ('week', 'month'):
        view = 'week'
    return redirect(_calendar_url(view, _parse_date(request.POST.get('date'))))
