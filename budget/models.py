from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q, Sum


class BudgetPeriodType(models.TextChoices):
    DAILY = 'DAILY', 'Daily'
    WEEKLY = 'WEEKLY', 'Weekly'
    MONTHLY = 'MONTHLY', 'Monthly'


class ExpenseCategory(models.Model):
    name = models.CharField(max_length=50, unique=True)

    class Meta:
        ordering = ('name',)
        verbose_name_plural = 'expense categories'

    def __str__(self):
        return self.name


class BudgetAllowance(models.Model):
    PeriodType = BudgetPeriodType

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='budget_allowances',
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    period_type = models.CharField(max_length=7, choices=BudgetPeriodType.choices)
    start_date = models.DateField()
    end_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-start_date',)
        constraints = [
            models.CheckConstraint(
                condition=Q(amount__gt=0),
                name='budget_allowance_amount_positive',
                violation_error_message='The allowance amount must be greater than zero.',
            ),
            models.CheckConstraint(
                condition=Q(end_date__gte=models.F('start_date')),
                name='budget_allowance_dates_valid',
                violation_error_message='The end date must be on or after the start date.',
            ),
            models.CheckConstraint(
                condition=Q(period_type__in=BudgetPeriodType.values),
                name='budget_allowance_period_valid',
                violation_error_message='Choose a valid allowance period.',
            ),
        ]

    def clean(self):
        super().clean()
        errors = {}
        if self.amount is not None and self.amount <= 0:
            errors['amount'] = 'The allowance amount must be greater than zero.'
        if self.start_date and self.end_date and self.end_date < self.start_date:
            errors['end_date'] = 'The end date must be on or after the start date.'

        if self.user_id and self.start_date and self.end_date:
            overlaps = type(self).objects.filter(
                user_id=self.user_id,
                start_date__lte=self.end_date,
                end_date__gte=self.start_date,
            )
            if self.pk:
                overlaps = overlaps.exclude(pk=self.pk)
            if overlaps.exists():
                errors['start_date'] = 'This allowance period overlaps another allowance.'

        if self.pk and self.start_date and self.end_date:
            outside_expenses = self.expenses.filter(
                Q(expense_date__lt=self.start_date) | Q(expense_date__gt=self.end_date)
            )
            if outside_expenses.exists():
                errors['end_date'] = 'The new dates must include all existing expense dates.'

        if errors:
            raise ValidationError(errors)

    @property
    def total_spent(self):
        return self.expenses.aggregate(total=Sum('amount'))['total'] or 0

    @property
    def remaining_budget(self):
        return self.amount - self.total_spent

    def __str__(self):
        return f'{self.user} - {self.get_period_type_display()} allowance ({self.start_date})'


class Expense(models.Model):
    allowance = models.ForeignKey(
        BudgetAllowance,
        on_delete=models.CASCADE,
        related_name='expenses',
    )
    category = models.ForeignKey(
        ExpenseCategory,
        on_delete=models.PROTECT,
        related_name='expenses',
    )
    item_name = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    expense_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-expense_date',)
        constraints = [
            models.CheckConstraint(
                condition=Q(amount__gt=0),
                name='budget_expense_amount_positive',
                violation_error_message='The expense amount must be greater than zero.',
            ),
        ]

    def clean(self):
        super().clean()
        errors = {}
        if self.amount is not None and self.amount <= 0:
            errors['amount'] = 'The expense amount must be greater than zero.'
        if (
            self.allowance_id
            and self.expense_date
            and not self.allowance.start_date <= self.expense_date <= self.allowance.end_date
        ):
            errors['expense_date'] = 'The expense date must be within the allowance period.'
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f'{self.item_name} - {self.amount} ({self.expense_date})'
