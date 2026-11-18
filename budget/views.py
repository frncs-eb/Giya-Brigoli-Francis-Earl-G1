from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import DecimalField, ExpressionWrapper, F, Sum, Value
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .forms import BudgetAllowanceForm, ExpenseFilterForm, ExpenseForm
from .models import BudgetAllowance, Expense


def allowances_for(user):
    return BudgetAllowance.objects.filter(user=user).annotate(
        spent_total=Coalesce(
            Sum('expenses__amount'),
            Value(Decimal('0.00')),
            output_field=DecimalField(max_digits=10, decimal_places=2),
        ),
    ).annotate(
        remaining=ExpressionWrapper(
            F('amount') - F('spent_total'),
            output_field=DecimalField(max_digits=11, decimal_places=2),
        ),
    )


def percentage(spent, amount):
    return spent * 100 / amount if amount else Decimal('0')


@login_required
def home(request):
    allowances = allowances_for(request.user).order_by('-start_date', '-created_at')
    today = timezone.localdate()
    summaries = []
    for allowance in allowances:
        used_percent = percentage(allowance.spent_total, allowance.amount)
        summaries.append({
            'allowance': allowance,
            'active': allowance.start_date <= today <= allowance.end_date,
            'progress_percent': min(used_percent, Decimal('100')),
            'used_percent': used_percent,
        })
    return render(request, 'budget/home.html', {'allowance_summaries': summaries})


@login_required
@require_http_methods(['GET', 'POST'])
def allowance_create(request):
    form = BudgetAllowanceForm(
        request.POST or None,
        user=request.user,
    )
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Your allowance has been created.')
        return redirect('budget:home')
    return render(request, 'budget/allowance_form.html', {
        'form': form,
        'title': 'Add allowance',
    })


@login_required
@require_http_methods(['GET', 'POST'])
def allowance_edit(request, pk):
    allowance = get_object_or_404(BudgetAllowance, pk=pk, user=request.user)
    form = BudgetAllowanceForm(
        request.POST or None,
        instance=allowance,
        user=request.user,
    )
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Your allowance has been updated.')
        return redirect('budget:allowance_detail', pk=allowance.pk)
    return render(request, 'budget/allowance_form.html', {
        'form': form,
        'title': 'Edit allowance',
        'allowance': allowance,
    })


@login_required
@require_http_methods(['GET', 'POST'])
def allowance_delete(request, pk):
    allowance = get_object_or_404(BudgetAllowance, pk=pk, user=request.user)
    if request.method == 'POST':
        allowance.delete()
        messages.success(request, 'Your allowance and its expenses have been deleted.')
        return redirect('budget:home')
    return render(request, 'budget/allowance_confirm_delete.html', {'allowance': allowance})


@login_required
def allowance_detail(request, pk):
    allowance = get_object_or_404(
        allowances_for(request.user).select_related('user'),
        pk=pk,
    )
    expenses = allowance.expenses.select_related('category')
    filter_form = ExpenseFilterForm(request.GET or None)
    if filter_form.is_valid():
        filters = filter_form.cleaned_data
        if filters['category']:
            expenses = expenses.filter(category=filters['category'])
        if filters['start_date']:
            expenses = expenses.filter(expense_date__gte=filters['start_date'])
        if filters['end_date']:
            expenses = expenses.filter(expense_date__lte=filters['end_date'])

    category_totals = list(
        expenses.values('category__name').annotate(total=Sum('amount')).order_by('-total')
    )
    filtered_total = sum((row['total'] for row in category_totals), Decimal('0.00'))
    for row in category_totals:
        row['percent'] = percentage(row['total'], filtered_total)

    total_spent = allowance.spent_total
    used_percent = percentage(total_spent, allowance.amount)
    context = {
        'allowance': allowance,
        'expenses': expenses,
        'filter_form': filter_form,
        'category_totals': category_totals,
        'filtered_total': filtered_total,
        'total_spent': total_spent,
        'remaining': allowance.amount - total_spent,
        'used_percent': used_percent,
        'progress_percent': min(used_percent, Decimal('100')),
    }
    return render(request, 'budget/allowance_detail.html', context)


@login_required
@require_http_methods(['GET', 'POST'])
def expense_create(request):
    initial = {}
    return_allowance = request.GET.get('allowance', '')
    if request.method == 'POST':
        return_allowance = request.POST.get('return_allowance', '')
    if return_allowance:
        origin = get_object_or_404(
            BudgetAllowance,
            pk=return_allowance,
            user=request.user,
        )
        initial['allowance'] = origin.pk

    form = ExpenseForm(
        request.POST or None,
        user=request.user,
        initial=initial,
    )
    if request.method == 'POST' and form.is_valid():
        expense = form.save()
        messages.success(request, 'Your expense has been added.')
        if return_allowance:
            return redirect('budget:allowance_detail', pk=origin.pk)
        return redirect('budget:allowance_detail', pk=expense.allowance_id)
    return render(request, 'budget/expense_form.html', {
        'form': form,
        'title': 'Add expense',
        'return_allowance': return_allowance,
    })


@login_required
@require_http_methods(['GET', 'POST'])
def expense_edit(request, pk):
    expense = get_object_or_404(
        Expense.objects.select_related('allowance'),
        pk=pk,
        allowance__user=request.user,
    )
    form = ExpenseForm(request.POST or None, instance=expense, user=request.user)
    if request.method == 'POST' and form.is_valid():
        expense = form.save()
        messages.success(request, 'Your expense has been updated.')
        return redirect('budget:allowance_detail', pk=expense.allowance_id)
    return render(request, 'budget/expense_form.html', {
        'form': form,
        'title': 'Edit expense',
        'expense': expense,
    })


@login_required
@require_http_methods(['GET', 'POST'])
def expense_delete(request, pk):
    expense = get_object_or_404(
        Expense.objects.select_related('allowance'),
        pk=pk,
        allowance__user=request.user,
    )
    allowance_id = expense.allowance_id
    if request.method == 'POST':
        expense.delete()
        messages.success(request, 'Your expense has been deleted.')
        return redirect('budget:allowance_detail', pk=allowance_id)
    return render(request, 'budget/expense_confirm_delete.html', {'expense': expense})
