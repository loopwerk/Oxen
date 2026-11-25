from datetime import timedelta
from typing import TypedDict

from django import forms
from django.core.exceptions import ValidationError
from django.db import transaction

from clients.models import Project

from .hours import format_hours, parse_hours
from .models import TimeEntry


class HoursField(forms.Field):
    """Hours typed as 1:30, 1.5 or 1,5; cleaned to minutes."""

    widget = forms.TextInput(attrs={"autocomplete": "off"})

    def to_python(self, value):
        if value in self.empty_values:
            return None
        try:
            return parse_hours(value)
        except ValueError:
            raise ValidationError("Use hours like 1:30, 1.5 or 1,5.", code="invalid") from None

    def prepare_value(self, value):
        # The initial value is minutes; submitted data stays as typed.
        if isinstance(value, int):
            return format_hours(value)
        return value


class Cell(TypedDict):
    minutes: int | None
    invoiced: bool
    field: forms.BoundField | None


class Row(TypedDict):
    project: Project
    cells: list[Cell]
    total: int


class WeekForm(forms.Form):
    """
    One field per editable cell: a project on a day of the week.
    Invoiced hours, and rows for archived or unassigned projects with hours that week, are read-only.
    """

    def __init__(self, *args, user, monday, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.days = [monday + timedelta(days=offset) for offset in range(7)]

        week_entries = TimeEntry.objects.filter(user=user, date__range=(self.days[0], self.days[-1]))
        self.entries = {
            (entry.project_id, entry.date): entry for entry in week_entries.select_related("project__client")
        }
        editable = set(
            user.accessible_projects().filter(archived=False, client__archived=False).select_related("client")
        )
        projects = editable | {entry.project for entry in self.entries.values()}

        self.cells = {}
        self.rows = []
        for project in sorted(projects, key=lambda project: (project.client.name.lower(), project.name.lower())):
            row: Row = {"project": project, "cells": [], "total": 0}
            for day in self.days:
                entry = self.entries.get((project.pk, day))
                minutes = entry.minutes if entry else None
                cell: Cell = {"minutes": minutes, "invoiced": bool(entry and entry.invoice_line_id), "field": None}
                if project in editable and not cell["invoiced"]:
                    name = f"{project.pk}-{day.isoformat()}"
                    self.fields[name] = HoursField(required=False, initial=minutes)
                    self.fields[name].widget.attrs["aria-label"] = f"{project.client} – {project}, {day:%A}"
                    self.cells[name] = (project, day)
                    cell["field"] = self[name]
                row["cells"].append(cell)
                row["total"] += minutes or 0
            self.rows.append(row)

        self.day_totals = [
            sum(entry.minutes for (_, date), entry in self.entries.items() if date == day) for day in self.days
        ]
        self.week_total = sum(self.day_totals)

    def save(self):
        with transaction.atomic():
            for name, (project, day) in self.cells.items():
                minutes = self.cleaned_data[name]
                entry = self.entries.get((project.pk, day))
                if not minutes:
                    if entry:
                        entry.delete()
                elif not entry:
                    TimeEntry.objects.create(user=self.user, project=project, date=day, minutes=minutes)
                elif entry.minutes != minutes:
                    entry.minutes = minutes
                    entry.save(update_fields=["minutes"])
