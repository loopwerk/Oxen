from decimal import ROUND_HALF_UP, Decimal

from babel.numbers import format_currency, get_currency_precision


def round_money(amount: Decimal, currency: str) -> Decimal:
    """Rounds half-up to the currency's own number of decimals: 2 for EUR, 0 for JPY."""
    exponent = Decimal(1).scaleb(-get_currency_precision(currency))
    return Decimal(amount).quantize(exponent, rounding=ROUND_HALF_UP)


def format_money(amount: Decimal, currency: str) -> str:
    """Always English style, such as €1,260.00 or ¥1,260."""
    return format_currency(amount, currency, locale="en")
