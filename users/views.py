from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_not_required
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.utils.decorators import method_decorator
from django.views import View

from .forms import AccountForm, LoginForm
from .passkeys import has_passkey
from .tokens import user_for_setup_link


@method_decorator(login_not_required, name="dispatch")
class LoginView(View):
    """Passkey login. django-otp-webauthn does the actual work in the browser."""

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("timesheets:index")

        form = LoginForm(initial={"next": request.GET.get("next", "")})
        return TemplateResponse(request, "users/login.html", {"form": form})


@method_decorator(login_not_required, name="dispatch")
class SetupLinkView(View):
    """
    The one-time link an admin passes on to a user. GET only shows a button, because link previews in chat apps open
    links too, and that mustn't use it up. POST logs the user in, so they can register a passkey.
    """

    def get(self, request, uidb64, token, *args, **kwargs):
        link_user = user_for_setup_link(uidb64, token)
        return TemplateResponse(request, "users/setup_link.html", {"link_user": link_user})

    def post(self, request, uidb64, token, *args, **kwargs):
        link_user = user_for_setup_link(uidb64, token)
        if link_user:
            login(request, link_user)
            return redirect("users:passkey")

        return TemplateResponse(request, "users/setup_link.html", {"link_user": None})


class PasskeySetupView(View):
    def get(self, request, *args, **kwargs):
        if has_passkey(request.user):
            return redirect("timesheets:index")

        return TemplateResponse(request, "users/passkey.html")


class AccountView(View):
    def get(self, request, *args, **kwargs):
        form = AccountForm(instance=request.user)
        return TemplateResponse(request, "users/account.html", {"form": form})

    def post(self, request, *args, **kwargs):
        form = AccountForm(data=request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Your account is saved.")
            return redirect("users:account")

        return TemplateResponse(request, "users/account.html", {"form": form})
