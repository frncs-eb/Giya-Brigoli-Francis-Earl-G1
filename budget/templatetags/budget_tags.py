from decimal import Decimal

from django import template

register = template.Library()


@register.filter
def money(value):
    if value is None:
        value = Decimal('0.00')
    return f'₱{value:,.2f}'
