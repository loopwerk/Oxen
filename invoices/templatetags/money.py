from decimal import Decimal

from babel.numbers import format_decimal
from django import template

from invoices.money import format_money

register = template.Library()


@register.filter
def money(amount: Decimal, currency: str) -> str:
    """{{ invoice.total|money:invoice.currency }} gives €1,260.00."""
    return format_money(amount, currency)


@register.filter
def quantity(value: Decimal) -> str:
    """Without trailing zeros: 96.00 gives 96, 1.50 gives 1.5."""
    return format_decimal(value, locale="en")


@register.filter
def percentage(rate: Decimal) -> str:
    """21.00 gives 21%, 9.50 gives 9.5%."""
    return f"{format_decimal(rate, locale='en')}%"
