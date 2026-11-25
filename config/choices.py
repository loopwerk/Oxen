"""Country choices from pycountry, currency choices from Babel, so we don't ship our own lists."""

import unicodedata
from functools import cache
from typing import cast

import pycountry
from babel import Locale
from babel.numbers import get_currency_precision, get_territory_currencies

ENGLISH = Locale("en")


def _sort_key(choice: tuple[str, str]) -> str:
    # Sort "Åland Islands" under A, not after Z.
    decomposed = unicodedata.normalize("NFKD", choice[1])
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


@cache
def country_choices() -> list[tuple[str, str]]:
    countries = [(country.alpha_2, getattr(country, "common_name", country.name)) for country in pycountry.countries]
    return sorted(countries, key=_sort_key)


@cache
def currency_choices() -> list[tuple[str, str]]:
    """Currencies in use today with 0 or 2 decimals, such as "Euro (EUR)" and "Japanese Yen (JPY)"."""
    codes = set()
    # Babel types the keys as str | int | None, but territory codes are strings.
    for territory in ENGLISH.territories:
        codes.update(get_territory_currencies(cast(str, territory), tender=True))
    currencies = [(code, f"{ENGLISH.currencies[code]} ({code})") for code in codes if get_currency_precision(code) <= 2]
    return sorted(currencies, key=_sort_key)
