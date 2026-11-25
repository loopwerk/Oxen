from django import template

from timesheets.hours import format_hours

register = template.Library()


@register.filter
def hours(minutes: int | None) -> str:
    """{{ entry.minutes|hours }} gives 1:30."""
    return format_hours(minutes)
