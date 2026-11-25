import json
import threading
import urllib.request
from datetime import datetime, timedelta
from urllib.parse import urlsplit

from django.conf import settings
from django.db import connection
from django.utils import timezone

from .models import UpdateCheck

CHECK_EVERY = timedelta(hours=24)


def _fetch_latest_version() -> str:
    """The latest release on GitHub, or "" when GitHub can't tell / is unreachable."""
    repository = urlsplit(settings.APP_REPOSITORY_URL).path.strip("/")
    request = urllib.request.Request(
        f"https://api.github.com/repos/{repository}/releases/latest",
        headers={"Accept": "application/vnd.github+json", "User-Agent": f"Oxen/{settings.APP_VERSION}"},
    )
    try:
        with urllib.request.urlopen(request, timeout=3) as response:
            return json.load(response)["tag_name"].removeprefix("v")
    except OSError, ValueError, KeyError, TypeError:
        return ""


def _store_latest_version() -> None:
    # Runs in its own thread, so it has its own database connection to close.
    try:
        latest = _fetch_latest_version()
        if latest:
            UpdateCheck.objects.filter(pk=1).update(latest_version=latest)
    finally:
        connection.close()


def start_update_check() -> datetime:
    """Asks GitHub in a background thread when the last check is over 24 hours old. Returns when the next one is due."""
    now = timezone.now()
    check = UpdateCheck.load()
    if check.checked_at and now - check.checked_at < CHECK_EVERY:
        return check.checked_at + CHECK_EVERY

    # Every attempt counts, also a failed one. Only the process whose update matches the row asks GitHub.
    if UpdateCheck.objects.filter(pk=check.pk, checked_at=check.checked_at).update(checked_at=now):
        threading.Thread(target=_store_latest_version, daemon=True).start()
    return now + CHECK_EVERY


def latest_version() -> str:
    """The latest released version that the last check found, or "" when unknown or turned off."""
    if not settings.UPDATE_CHECK:
        return ""
    return UpdateCheck.load().latest_version


def _version_tuple(version: str) -> tuple[int, ...] | None:
    """1.4.0 as (1, 4, 0), or None when it isn't a plain version number."""
    try:
        return tuple(int(part) for part in version.split("."))
    except ValueError:
        return None


def is_newer(version: str, than: str) -> bool:
    new, current = _version_tuple(version), _version_tuple(than)
    return new is not None and current is not None and new > current
