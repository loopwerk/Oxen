from django.conf import settings
from django.db import models

from .hours import format_hours


class TimeEntry(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="time_entries")
    project = models.ForeignKey("clients.Project", on_delete=models.PROTECT, related_name="time_entries")
    date = models.DateField()
    minutes = models.PositiveIntegerField()
    notes = models.TextField(blank=True)
    invoice_line = models.ForeignKey(
        "invoices.InvoiceLine",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="time_entries",
    )

    class Meta:
        verbose_name_plural = "time entries"
        ordering = ["date"]
        constraints = [
            models.UniqueConstraint(fields=["user", "project", "date"], name="timeentry_unique_user_project_date"),
        ]

    def __str__(self):
        return f"{self.date} {self.project}: {format_hours(self.minutes)}"
