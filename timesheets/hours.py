import re
from decimal import ROUND_HALF_UP, Decimal

CLOCK = re.compile(r"^(\d{1,3}):([0-5]\d)$")
DECIMAL = re.compile(r"^(\d{1,3}|\d{0,3}[.,]\d+)$")


def parse_hours(value: str) -> int | None:
    """Minutes from 1:30, 1.5, 1,5 or 2 (2:00). Empty gives None; anything else raises ValueError."""
    value = value.strip()
    if not value:
        return None

    if match := CLOCK.match(value):
        return int(match[1]) * 60 + int(match[2])

    if DECIMAL.match(value):
        hours = Decimal(value.replace(",", "."))
        return int((hours * 60).to_integral_value(ROUND_HALF_UP))

    raise ValueError(f"Not a number of hours: {value!r}")


def format_hours(minutes: int | None) -> str:
    """Format minutes: 90 gives 1:30. None gives an empty string."""
    if minutes is None:
        return ""
    return f"{minutes // 60}:{minutes % 60:02d}"
