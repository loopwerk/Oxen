from dataclasses import dataclass
from datetime import date, timedelta

from django.db.models import Q
from django.utils import dateformat


@dataclass(frozen=True)
class Period:
    """Which hours an invoice from hours covers. Without a start and end, that's all of them."""

    key: str
    label: str
    subject: str
    start: date | None = None
    end: date | None = None

    def q(self) -> Q:
        """A filter for the time entries in this period."""
        if self.start is None:
            return Q()
        return Q(date__range=(self.start, self.end))


def _months_later(first: date, months: int) -> date:
    """The first day of the month that many months later, or earlier when negative."""
    index = first.year * 12 + first.month - 1 + months
    return date(index // 12, index % 12 + 1, 1)


def _month(key: str, label: str, first: date) -> Period:
    name = dateformat.format(first, "F")
    end = _months_later(first, 1) - timedelta(days=1)
    return Period(key, f"{label} ({name})", f"{name} {first.year}", first, end)


def _quarter(key: str, label: str, first: date) -> Period:
    number = (first.month - 1) // 3 + 1
    end = _months_later(first, 3) - timedelta(days=1)
    return Period(key, f"{label} (Q{number})", f"Q{number} {first.year}", first, end)


def _year(key: str, label: str, number: int) -> Period:
    return Period(key, f"{label} ({number})", str(number), date(number, 1, 1), date(number, 12, 31))


def periods(today: date) -> dict[str, Period]:
    """The periods to pick from, by key."""
    this_month = today.replace(day=1)
    this_quarter = this_month.replace(month=(today.month - 1) // 3 * 3 + 1)
    choices = [
        Period("all", "All uninvoiced hours", ""),
        _month("this_month", "This month", this_month),
        _month("last_month", "Last month", _months_later(this_month, -1)),
        _quarter("this_quarter", "This quarter", this_quarter),
        _quarter("last_quarter", "Last quarter", _months_later(this_quarter, -3)),
        _year("this_year", "This year", today.year),
        _year("last_year", "Last year", today.year - 1),
    ]
    return {period.key: period for period in choices}
