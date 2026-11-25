from django.http import HttpRequest

from .models import User


class AuthenticatedHttpRequest(HttpRequest):
    """A request with a logged-in user: LoginRequiredMiddleware guarantees that unless a view is @login_not_required."""

    user: User
