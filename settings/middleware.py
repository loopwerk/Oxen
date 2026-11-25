from django.conf import settings
from django.utils import timezone

from .updates import start_update_check


class UpdateCheckMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.next_check = None

    def __call__(self, request):
        due = self.next_check is None or timezone.now() >= self.next_check
        if settings.UPDATE_CHECK and due and request.user.is_authenticated and request.user.is_admin:
            self.next_check = start_update_check()
        return self.get_response(request)
