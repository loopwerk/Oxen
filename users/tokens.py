from django.conf import settings
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from .models import User
from .passkeys import has_passkey


class SetupLinkTokenGenerator(PasswordResetTokenGenerator):
    key_salt = "users.tokens.SetupLinkTokenGenerator"


setup_link_tokens = SetupLinkTokenGenerator()


def setup_link(user: User) -> str:
    """The absolute URL an admin passes on to the user."""
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = setup_link_tokens.make_token(user)
    return settings.APP_URL + reverse("users:setup", kwargs={"uidb64": uidb64, "token": token})


def user_for_setup_link(uidb64: str, token: str) -> User | None:
    """The user a setup link is for, or None if it's invalid, used, expired, or the user already has a passkey."""
    try:
        user = User.objects.get(pk=urlsafe_base64_decode(uidb64).decode(), is_active=True)
    except ValueError, User.DoesNotExist:
        return None

    if has_passkey(user) or not setup_link_tokens.check_token(user, token):
        return None

    return user
