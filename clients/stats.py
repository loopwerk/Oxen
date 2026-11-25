from datetime import timedelta
from decimal import Decimal

from django.db.models import Q, QuerySet, Sum
from django.utils import timezone

from invoices.models import InvoiceLine
from invoices.money import round_money
from timesheets.models import TimeEntry


def hour_totals(entries: QuerySet[TimeEntry]) -> dict[str, int]:
    """Minutes this week, month, year and all time, and how many of them are invoiced or not."""
    today = timezone.localdate()
    monday = today - timedelta(days=today.weekday())
    return entries.aggregate(
        week=Sum("minutes", filter=Q(date__range=(monday, monday + timedelta(days=6))), default=0),
        month=Sum("minutes", filter=Q(date__year=today.year, date__month=today.month), default=0),
        year=Sum("minutes", filter=Q(date__year=today.year), default=0),
        all_time=Sum("minutes", default=0),
        invoiced=Sum("minutes", filter=Q(invoice_line__isnull=False), default=0),
        uninvoiced=Sum("minutes", filter=Q(invoice_line__isnull=True), default=0),
    )


def invoiced_amounts(entries: QuerySet[TimeEntry]) -> dict[str, Decimal]:
    """The invoice lines with these hours, before tax. Per currency, because a client's currency can change between invoices."""
    amounts: dict[str, Decimal] = {}
    for line in InvoiceLine.objects.filter(time_entries__in=entries).distinct().select_related("invoice"):
        amounts.setdefault(line.invoice.currency, Decimal(0))
        amounts[line.invoice.currency] += line.amount
    return amounts


def uninvoiced_amount(minutes: int, hourly_rate: Decimal, currency: str) -> Decimal:
    """Rounded once per project, like an invoice line from hours."""
    return round_money(minutes * hourly_rate / 60, currency)
