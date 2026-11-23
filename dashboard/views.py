from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.db.models import DecimalField, ExpressionWrapper, F, Sum, Value
from django.db.models.functions import Coalesce
from django.shortcuts import render
from django.utils import timezone

from budget.models import BudgetAllowance, Expense
from clinical.models import ClinicalLog
from schedule.models import ClassSchedule


def allowance_spending(queryset):
    return queryset.annotate(
        spent_total=Coalesce(
            Sum('expenses__amount'),
            Value(0),
            output_field=DecimalField(max_digits=10, decimal_places=2),
        ),
    ).annotate(
        remaining=ExpressionWrapper(
            F('amount') - F('spent_total'),
            output_field=DecimalField(max_digits=11, decimal_places=2),
        ),
    )


@login_required
def home(request):
    user = request.user
    if user.is_staff:
        users = get_user_model().objects.all()
        context = {
            'total_users': users.count(),
            'active_users': users.filter(is_active=True).count(),
            'inactive_users': users.filter(is_active=False).count(),
            'admin_count': users.filter(is_staff=True).count(),
            'user_count': users.filter(is_staff=False).count(),
            'recent_users': users.order_by('-date_joined')[:5],
        }
        return render(request, 'dashboard/admin.html', context)

    today = timezone.localdate()
    user_expenses = Expense.objects.filter(allowance__user=user)
    today_spent = user_expenses.filter(expense_date=today).aggregate(
        total=Sum('amount'),
    )['total'] or Decimal('0.00')
    month_to_date = user_expenses.filter(
        expense_date__gte=date(today.year, today.month, 1),
        expense_date__lte=today,
    )
    month_spent = month_to_date.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    category_spending = list(
        month_to_date.values('category__name').annotate(
            total=Sum('amount'),
        ).order_by('-total')
    )
    for category in category_spending:
        category['percent'] = (
            category['total'] * 100 / month_spent if month_spent else Decimal('0')
        )

    active_allowance = allowance_spending(
        BudgetAllowance.objects.filter(
            user=user,
            start_date__lte=today,
            end_date__gte=today,
        )
    ).order_by('-start_date', '-created_at').first()
    budget_summary = None
    if active_allowance:
        budget_summary = {
            'allowance': active_allowance,
            'progress_percent': min(
                active_allowance.spent_total * 100 / active_allowance.amount,
                100,
            ),
            'used_percent': active_allowance.spent_total * 100 / active_allowance.amount,
        }
    recent_expenses = user_expenses.select_related(
        'category',
        'allowance',
    ).order_by('-expense_date', '-created_at')[:5]
    upcoming_classes = []
    now = timezone.localtime()
    for class_item in ClassSchedule.objects.filter(user=user):
        days_ahead = (class_item.day_of_week - 1 - today.weekday()) % 7
        occurrence = today + timedelta(days=days_ahead)
        if occurrence == today and class_item.start_time <= now.time():
            occurrence += timedelta(days=7)
        upcoming_classes.append({'class_item': class_item, 'date': occurrence})
    upcoming_classes.sort(key=lambda item: (item['date'], item['class_item'].start_time))
    recent_clinical_logs = ClinicalLog.objects.filter(user=user).order_by(
        '-duty_date', '-duty_time',
    )[:3]
    return render(request, 'dashboard/user.html', {
        'budget_summary': budget_summary,
        'today': today,
        'today_spent': today_spent,
        'month_spent': month_spent,
        'category_spending': category_spending,
        'recent_expenses': recent_expenses,
        'upcoming_classes': upcoming_classes[:3],
        'recent_clinical_logs': recent_clinical_logs,
    })
