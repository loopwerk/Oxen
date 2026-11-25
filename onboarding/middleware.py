from django.shortcuts import redirect
from django_otp_webauthn.utils import get_credential_model

# These are accessible during onboarding: the wizard itself, passkey registration, and the dev server's browser reload.
ONBOARDING_NAMESPACES = {"onboarding", "otp_webauthn", "django_browser_reload"}


def setup_done():
    # Setup is done once any user has registered a passkey
    return get_credential_model().objects.filter(confirmed=True).exists()


class OnboardingMiddleware:
    """Sends every page to the onboarding wizard until a user has registered a passkey."""

    def __init__(self, get_response):
        self.get_response = get_response
        self.done = False

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        if self.done:
            return None

        if request.resolver_match.namespace in ONBOARDING_NAMESPACES:
            return None

        if setup_done():
            self.done = True
            return None

        return redirect("onboarding:account")
