from datetime import date, timedelta
from typing import Any
from urllib.parse import urlencode

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils import dateformat, timezone
from django.views import View

from clients.models import Client
from users.http import AuthenticatedHttpRequest
from users.models import User

from .forms import WeekForm


def _monday_of(day: date) -> date:
    return day - timedelta(days=day.weekday())


def _week_range(monday: date) -> str:
    """09 - 15 Nov 2026, 26 Oct - 01 Nov 2026, or 28 Dec 2026 - 03 Jan 2027."""
    sunday = monday + timedelta(days=6)
    if monday.year != sunday.year:
        start = dateformat.format(monday, "d M Y")
    elif monday.month != sunday.month:
        start = dateformat.format(monday, "d M")
    else:
        start = dateformat.format(monday, "d")
    return f"{start} - {dateformat.format(sunday, 'd M Y')}"


def _week_user(request: AuthenticatedHttpRequest) -> User:
    """Admins open anyone's week with ?user=<username>; everyone else only has their own."""
    username = request.GET.get("user")
    if not username or username == request.user.username:
        return request.user
    if not request.user.is_admin:
        raise PermissionDenied
    return get_object_or_404(User, username=username)


def _week_url(request: AuthenticatedHttpRequest, monday: date, user: User) -> str:
    """The current week lives at /, other weeks at their Monday's date."""
    if monday == _monday_of(timezone.localdate()):
        url = reverse("timesheets:index")
    else:
        url = reverse("timesheets:week", args=[monday])
    if user != request.user:
        url += "?" + urlencode({"user": user.username})
    return url


def _week_context(request: AuthenticatedHttpRequest, form: WeekForm, monday: date, user: User) -> dict[str, Any]:
    this_monday = _monday_of(timezone.localdate())
    users = list(User.objects.filter(is_active=True).order_by("name", "username")) if request.user.is_admin else []
    return {
        "form": form,
        "week_range": _week_range(monday),
        "week_user": user,
        "previous_url": _week_url(request, monday - timedelta(weeks=1), user),
        "next_url": _week_url(request, monday + timedelta(weeks=1), user),
        "this_week_url": _week_url(request, this_monday, user) if monday != this_monday else None,
        "users": users if len(users) > 1 else [],
        "has_clients": Client.objects.filter(archived=False).exists(),
    }


class WeekView(View):
    def get(self, request, day=None, *args, **kwargs):
        user = _week_user(request)
        monday = _monday_of(day or timezone.localdate())
        if day and day != monday:
            return redirect(_week_url(request, monday, user))

        form = WeekForm(user=user, monday=monday)
        return TemplateResponse(request, "timesheets/index.html", _week_context(request, form, monday, user))

    def post(self, request, day=None, *args, **kwargs):
        user = _week_user(request)
        monday = _monday_of(day or timezone.localdate())
        form = WeekForm(data=request.POST, user=user, monday=monday)
        if form.is_valid():
            form.save()
            messages.success(request, "The hours are saved.")
            return redirect(request.get_full_path())

        return TemplateResponse(request, "timesheets/index.html", _week_context(request, form, monday, user))
