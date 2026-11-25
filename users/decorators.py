from collections.abc import Callable
from functools import wraps

from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponseBase


def admin_required(view: Callable[..., HttpResponseBase]) -> Callable[..., HttpResponseBase]:
    @wraps(view)
    def wrapper(request: HttpRequest, *args, **kwargs) -> HttpResponseBase:
        if not request.user.is_authenticated or not request.user.is_admin:
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return wrapper
