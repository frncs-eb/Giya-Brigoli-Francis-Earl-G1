from decimal import Decimal

from django import forms

from .models import BudgetAllowance, Expense, ExpenseCategory


class BudgetAllowanceForm(forms.ModelForm):
    amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal('0.01'),
        error_messages={'min_value': 'The allowance amount must be greater than zero.'},
    )

    class Meta:
        model = BudgetAllowance
        fields = ('amount', 'period_type', 'start_date', 'end_date')
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.instance.user = user

    def save(self, commit=True):
        allowance = super().save(commit=False)
        allowance.user = self.user
        if commit:
            allowance.save()
            self.save_m2m()
        return allowance


class ExpenseForm(forms.ModelForm):
    amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal('0.01'),
        error_messages={'min_value': 'The expense amount must be greater than zero.'},
    )

    class Meta:
        model = Expense
        fields = ('allowance', 'category', 'item_name', 'amount', 'expense_date')
        widgets = {'expense_date': forms.DateInput(attrs={'type': 'date'})}

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['allowance'].queryset = BudgetAllowance.objects.filter(
            user=user,
        ).order_by('-start_date', '-created_at')


class ExpenseFilterForm(forms.Form):
    category = forms.ModelChoiceField(
        queryset=ExpenseCategory.objects.none(),
        required=False,
        empty_label='All categories',
    )
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
    )
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = ExpenseCategory.objects.all()

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        if start_date and end_date and end_date < start_date:
            self.add_error('end_date', 'End date must be on or after start date.')
        return cleaned_data
