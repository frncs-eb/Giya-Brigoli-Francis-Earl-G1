from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .forms import BudgetAllowanceForm, ExpenseForm
from .models import BudgetAllowance, Expense, ExpenseCategory


class BudgetModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.user = user_model.objects.create_user(username='budget-user', password='pass12345')
        cls.category = ExpenseCategory.objects.create(name='Test category')

    def make_allowance(self, **kwargs):
        values = {
            'user': self.user,
            'amount': Decimal('100.00'),
            'period_type': BudgetAllowance.PeriodType.MONTHLY,
            'start_date': date(2026, 1, 1),
            'end_date': date(2026, 1, 31),
        }
        values.update(kwargs)
        return BudgetAllowance(**values)

    def test_constraints_reject_nonpositive_amount_and_invalid_dates(self):
        for allowance in (
            self.make_allowance(amount=Decimal('0.00')),
            self.make_allowance(period_type='YEARLY'),
            self.make_allowance(
                start_date=date(2026, 2, 1),
                end_date=date(2026, 1, 31),
            ),
        ):
            with self.subTest(allowance=allowance):
                with self.assertRaises(ValidationError):
                    allowance.full_clean()

        allowance = self.make_allowance()
        allowance.save()
        invalid_expense = Expense(
            allowance=allowance,
            category=self.category,
            item_name='Invalid amount',
            amount=Decimal('0.00'),
            expense_date=date(2026, 1, 10),
        )
        with self.assertRaises(ValidationError):
            invalid_expense.full_clean()

    def test_overlap_rejected_but_edit_does_not_conflict_with_itself(self):
        existing = self.make_allowance()
        existing.save()
        overlap = self.make_allowance(
            start_date=date(2026, 1, 31),
            end_date=date(2026, 2, 20),
        )
        with self.assertRaises(ValidationError):
            overlap.full_clean()

        existing.amount = Decimal('120.00')
        existing.full_clean()

    def test_expense_date_must_be_within_allowance(self):
        allowance = self.make_allowance()
        allowance.save()
        expense = Expense(
            allowance=allowance,
            category=self.category,
            item_name='Outside period',
            amount=Decimal('10.00'),
            expense_date=date(2026, 2, 1),
        )
        with self.assertRaises(ValidationError):
            expense.full_clean()

    def test_remaining_budget_for_no_expenses_and_several_expenses(self):
        allowance = self.make_allowance()
        allowance.save()
        self.assertEqual(allowance.remaining_budget, Decimal('100.00'))

        Expense.objects.create(
            allowance=allowance,
            category=self.category,
            item_name='First',
            amount=Decimal('12.25'),
            expense_date=date(2026, 1, 3),
        )
        Expense.objects.create(
            allowance=allowance,
            category=self.category,
            item_name='Second',
            amount=Decimal('28.25'),
            expense_date=date(2026, 1, 8),
        )
        allowance.refresh_from_db()
        self.assertEqual(allowance.total_spent, Decimal('40.50'))
        self.assertEqual(allowance.remaining_budget, Decimal('59.50'))

    def test_allowance_edit_cannot_leave_existing_expenses_outside_period(self):
        allowance = self.make_allowance()
        allowance.save()
        Expense.objects.create(
            allowance=allowance,
            category=self.category,
            item_name='Existing',
            amount=Decimal('10.00'),
            expense_date=date(2026, 1, 30),
        )
        allowance.end_date = date(2026, 1, 29)
        with self.assertRaises(ValidationError):
            allowance.full_clean()

    def test_category_with_expenses_is_protected(self):
        allowance = self.make_allowance()
        allowance.save()
        Expense.objects.create(
            allowance=allowance,
            category=self.category,
            item_name='Protected',
            amount=Decimal('10.00'),
            expense_date=date(2026, 1, 10),
        )
        with self.assertRaises(ProtectedError):
            self.category.delete()

    def test_seeded_categories_exist_after_migrations(self):
        self.assertTrue(
            ExpenseCategory.objects.filter(
                name__in=('Food', 'Materials', 'Transportation', 'Others')
            ).count() == 4
        )

    def test_model_forms_apply_overlap_and_date_rules(self):
        self.make_allowance().save()
        allowance_form = BudgetAllowanceForm(
            {
                'amount': '90.00',
                'period_type': BudgetAllowance.PeriodType.MONTHLY,
                'start_date': '2026-01-15',
                'end_date': '2026-02-01',
            },
            user=self.user,
        )
        self.assertFalse(allowance_form.is_valid())
        self.assertIn('overlaps', str(allowance_form.errors))

        allowance = BudgetAllowance.objects.first()
        expense_form = ExpenseForm(
            {
                'allowance': allowance.pk,
                'category': self.category.pk,
                'item_name': 'Outside',
                'amount': '10.00',
                'expense_date': '2026-02-01',
            },
            user=self.user,
        )
        self.assertFalse(expense_form.is_valid())
        self.assertIn('within the allowance period', str(expense_form.errors))


class BudgetViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.user = user_model.objects.create_user(username='owner', password='pass12345')
        cls.other_user = user_model.objects.create_user(username='other', password='pass12345')
        cls.category = ExpenseCategory.objects.get(name='Food')

    def make_allowance(self, user=None):
        today = timezone.localdate()
        return BudgetAllowance.objects.create(
            user=user or self.user,
            amount=Decimal('100.00'),
            period_type=BudgetAllowance.PeriodType.MONTHLY,
            start_date=date(today.year, 1, 1),
            end_date=date(today.year, 12, 31),
        )

    def make_expense(self, allowance):
        return Expense.objects.create(
            allowance=allowance,
            category=self.category,
            item_name='Lunch',
            amount=Decimal('12.50'),
            expense_date=timezone.localdate(),
        )

    def test_other_user_records_return_404_for_view_edit_and_delete(self):
        allowance = self.make_allowance(self.other_user)
        expense = self.make_expense(allowance)
        self.client.force_login(self.user)
        for url in (
            reverse('budget:allowance_detail', args=(allowance.pk,)),
            reverse('budget:allowance_edit', args=(allowance.pk,)),
            reverse('budget:allowance_delete', args=(allowance.pk,)),
            reverse('budget:expense_edit', args=(expense.pk,)),
            reverse('budget:expense_delete', args=(expense.pk,)),
        ):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 404)

    def test_anonymous_users_are_redirected_to_login(self):
        response = self.client.get(reverse('budget:home'))
        self.assertRedirects(
            response,
            f'{reverse("accounts:login")}?next={reverse("budget:home")}',
        )

    def test_delete_actions_only_delete_on_post(self):
        allowance = self.make_allowance()
        expense = self.make_expense(allowance)
        self.client.force_login(self.user)
        self.assertEqual(
            self.client.get(reverse('budget:allowance_delete', args=(allowance.pk,))).status_code,
            200,
        )
        self.assertTrue(BudgetAllowance.objects.filter(pk=allowance.pk).exists())
        self.assertEqual(
            self.client.get(reverse('budget:expense_delete', args=(expense.pk,))).status_code,
            200,
        )
        self.assertTrue(Expense.objects.filter(pk=expense.pk).exists())
        self.assertEqual(
            self.client.put(reverse('budget:allowance_delete', args=(allowance.pk,))).status_code,
            405,
        )

    def test_expense_allowance_choices_are_limited_to_current_user(self):
        own = self.make_allowance()
        self.make_allowance(self.other_user)
        self.client.force_login(self.user)
        response = self.client.get(reverse('budget:expense_create'))
        self.assertContains(response, f'value="{own.pk}"')
        self.assertEqual(
            list(response.context['form'].fields['allowance'].queryset.values_list('pk', flat=True)),
            [own.pk],
        )

    def test_dashboard_displays_budget_with_and_without_active_allowance(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('dashboard:home'))
        self.assertContains(response, 'No active allowance')

        allowance = self.make_allowance()
        self.make_expense(allowance)
        response = self.client.get(reverse('dashboard:home'))
        self.assertContains(response, 'Budget')
        self.assertContains(response, '₱87.50')
        self.assertContains(response, '₱12.50')
        self.assertContains(response, 'Spent today')
        self.assertContains(response, 'This month')
        self.assertContains(response, 'Where your money goes')
        self.assertContains(response, 'Recent expenses')
        self.assertContains(response, 'Savings goals')

    def test_dashboard_spending_data_is_limited_to_signed_in_user(self):
        self.client.force_login(self.user)
        allowance = self.make_allowance(self.other_user)
        self.make_expense(allowance)

        response = self.client.get(reverse('dashboard:home'))

        self.assertContains(response, '₱0.00')
        self.assertNotContains(response, 'Lunch')

    def test_expense_create_from_allowance_returns_to_detail(self):
        allowance = self.make_allowance()
        self.client.force_login(self.user)
        url = f'{reverse("budget:expense_create")}?allowance={allowance.pk}'
        response = self.client.post(url, {
            'allowance': allowance.pk,
            'category': self.category.pk,
            'item_name': 'Meal',
            'amount': '15.00',
            'expense_date': '2026-05-01',
            'return_allowance': allowance.pk,
        })
        self.assertRedirects(response, reverse('budget:allowance_detail', args=(allowance.pk,)))
