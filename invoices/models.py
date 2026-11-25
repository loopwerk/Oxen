from decimal import Decimal
from functools import cached_property

from django.db import models
from django.db.models import Max, Q
from django.utils import timezone

from config.choices import currency_choices

from .money import round_money


class Invoice(models.Model):
    client = models.ForeignKey("clients.Client", on_delete=models.PROTECT, related_name="invoices")
    number = models.CharField(max_length=50, unique=True)
    issue_date = models.DateField()
    due_date = models.DateField()
    paid_on = models.DateField(null=True, blank=True)
    subject = models.CharField(max_length=255, blank=True)
    currency = models.CharField(max_length=3, choices=currency_choices)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="Tax rate (%)")

    class Meta:
        ordering = ["-issue_date", "-number"]

    def __str__(self):
        return self.number

    @property
    def status(self):
        if self.paid_on:
            return "paid"
        if timezone.localdate() > self.due_date:
            return "overdue"
        return "open"

    @staticmethod
    def status_filters():
        """A filter per status, derived the same way as `status`."""
        today = timezone.localdate()
        return {
            "open": Q(paid_on__isnull=True, due_date__gte=today),
            "overdue": Q(paid_on__isnull=True, due_date__lt=today),
            "paid": Q(paid_on__isnull=False),
        }

    @cached_property
    def subtotal(self):
        return sum((line.amount for line in self.lines.all()), Decimal(0))

    @cached_property
    def tax(self):
        return round_money(self.subtotal * self.tax_rate / 100, self.currency)

    @cached_property
    def total(self):
        return self.subtotal + self.tax


def next_invoice_number(year):
    """Invoice numbers are YYYY-NNNN: the next sequence number within the year, starting at 0001."""
    last = Invoice.objects.filter(number__startswith=f"{year}-").aggregate(Max("number"))["number__max"]
    sequence = int(last.split("-")[1]) + 1 if last else 1
    return f"{year}-{sequence:04d}"


class InvoiceLine(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="lines")
    position = models.PositiveSmallIntegerField()
    description = models.TextField()
    minutes = models.IntegerField(null=True, blank=True)
    quantity = models.DecimalField(null=True, blank=True, max_digits=10, decimal_places=2)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ["position"]
        constraints = [
            models.CheckConstraint(
                condition=Q(minutes__isnull=False, quantity__isnull=True)
                | Q(minutes__isnull=True, quantity__isnull=False),
                name="invoiceline_minutes_or_quantity",
            ),
        ]

    def __str__(self):
        return self.description

    @property
    def amount(self):
        if self.minutes is not None:
            return round_money(self.minutes * self.unit_price / 60, self.invoice.currency)
        assert self.quantity is not None  # The check constraint requires minutes or a quantity.
        return round_money(self.quantity * self.unit_price, self.invoice.currency)
