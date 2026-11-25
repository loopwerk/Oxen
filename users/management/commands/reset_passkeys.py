from django.core.management.base import BaseCommand, CommandError

from users.models import User
from users.passkeys import reset_passkeys
from users.tokens import setup_link


class Command(BaseCommand):
    help = "Deletes a user's passkeys and prints a new setup link. Handy for an admin who is locked out."

    def add_arguments(self, parser):
        parser.add_argument("username")

    def handle(self, *args, username, **options):
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f"There's no user called {username!r}.") from None

        if not user.is_active:
            raise CommandError(f"{username} is inactive, so a setup link wouldn't let them log in.")

        reset_passkeys(user)
        self.stdout.write(f"{user}'s passkeys are deleted. This setup link works for an hour:")
        self.stdout.write(setup_link(user))
