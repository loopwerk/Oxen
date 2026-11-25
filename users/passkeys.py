from django.db import transaction
from django.db.models import Exists, OuterRef, QuerySet
from django_otp_webauthn.models import AbstractWebAuthnCredential
from django_otp_webauthn.utils import get_credential_model

from .models import User


def _passkeys_for(user: User) -> QuerySet[AbstractWebAuthnCredential]:
    return get_credential_model().objects.filter(user=user, confirmed=True)


def has_passkey(user: User) -> bool:
    return _passkeys_for(user).exists()


def annotate_has_passkey(users: QuerySet[User]) -> QuerySet[User]:
    """Adds `has_passkey` to each user in a queryset, in the same query."""
    passkeys = get_credential_model().objects.filter(user=OuterRef("pk"), confirmed=True)
    return users.annotate(has_passkey=Exists(passkeys))


def reset_passkeys(user: User) -> None:
    """For a lost device. A new unusable password also logs the user out everywhere and voids older setup links."""
    with transaction.atomic():
        get_credential_model().objects.filter(user=user).delete()
        user.set_unusable_password()
        user.save(update_fields=["password"])
