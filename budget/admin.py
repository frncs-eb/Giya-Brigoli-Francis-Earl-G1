from django.contrib import admin, messages
from django.db.models import ProtectedError

from .models import BudgetAllowance, Expense, ExpenseCategory


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

    def delete_model(self, request, obj):
        try:
            super().delete_model(request, obj)
        except ProtectedError:
            self.message_user(
                request,
                'This category cannot be deleted because it has expenses.',
                level=messages.ERROR,
            )

    def delete_queryset(self, request, queryset):
        try:
            super().delete_queryset(request, queryset)
        except ProtectedError:
            self.message_user(
                request,
                'One or more categories cannot be deleted because they have expenses.',
                level=messages.ERROR,
            )


@admin.register(BudgetAllowance)
class BudgetAllowanceAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'period_type', 'start_date', 'end_date', 'created_at')
    list_filter = ('period_type', 'start_date', 'end_date')
    search_fields = ('user__username',)
    autocomplete_fields = ('user',)


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('item_name', 'allowance', 'category', 'amount', 'expense_date')
    list_filter = ('category', 'expense_date')
    search_fields = ('item_name', 'allowance__user__username')
    autocomplete_fields = ('allowance', 'category')
