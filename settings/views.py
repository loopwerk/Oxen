from django.conf import settings
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.utils.decorators import method_decorator
from django.views import View

from users.decorators import admin_required
from users.forms import UserCreateForm, UserEditForm
from users.models import User
from users.passkeys import annotate_has_passkey, has_passkey, reset_passkeys
from users.tokens import setup_link

from .forms import CompanyForm
from .models import Company
from .updates import is_newer, latest_version


@method_decorator(admin_required, name="dispatch")
class SettingsView(View):
    def get(self, request, *args, **kwargs):
        return redirect("settings:company")


@method_decorator(admin_required, name="dispatch")
class CompanySettingsView(View):
    def get(self, request, *args, **kwargs):
        company = Company.load()
        form = CompanyForm(instance=company)
        return TemplateResponse(request, "settings/company.html", {"form": form, "company": company})

    def post(self, request, *args, **kwargs):
        company = Company.load()
        form = CompanyForm(data=request.POST, files=request.FILES, instance=company)
        if form.is_valid():
            form.save()
            messages.success(request, "Your company details are saved.")
            return redirect("settings:company")

        return TemplateResponse(request, "settings/company.html", {"form": form, "company": company})


@method_decorator(admin_required, name="dispatch")
class UserListView(View):
    def get(self, request, *args, **kwargs):
        users = annotate_has_passkey(User.objects.order_by("username"))
        return TemplateResponse(request, "settings/users.html", {"users": users})


@method_decorator(admin_required, name="dispatch")
class UserCreateView(View):
    def get(self, request, *args, **kwargs):
        return TemplateResponse(request, "settings/user_form.html", {"form": UserCreateForm()})

    def post(self, request, *args, **kwargs):
        form = UserCreateForm(data=request.POST)
        if form.is_valid():
            new_user = form.save(commit=False)
            new_user.set_unusable_password()
            new_user.save()
            form.save_m2m()
            return redirect("settings:user-setup-link", pk=new_user.pk)

        return TemplateResponse(request, "settings/user_form.html", {"form": form})


@method_decorator(admin_required, name="dispatch")
class UserEditView(View):
    """Other users only: your own details are on your Account page, so you can't take away your own admin rights."""

    def get(self, request, pk, *args, **kwargs):
        if pk == request.user.pk:
            return redirect("users:account")

        edited_user = get_object_or_404(User, pk=pk)
        form = UserEditForm(instance=edited_user)
        context = {"form": form, "edited_user": edited_user, "has_passkey": has_passkey(edited_user)}
        return TemplateResponse(request, "settings/user_form.html", context)

    def post(self, request, pk, *args, **kwargs):
        if pk == request.user.pk:
            return redirect("users:account")

        edited_user = get_object_or_404(User, pk=pk)
        form = UserEditForm(data=request.POST, instance=edited_user)
        if form.is_valid():
            form.save()
            messages.success(request, f"{edited_user} is saved.")
            return redirect("settings:users")

        context = {"form": form, "edited_user": edited_user, "has_passkey": has_passkey(edited_user)}
        return TemplateResponse(request, "settings/user_form.html", context)


@method_decorator(admin_required, name="dispatch")
class UserSetupLinkView(View):
    """A fresh setup link each time, for a user who doesn't have a passkey (yet)."""

    def get(self, request, pk, *args, **kwargs):
        edited_user = get_object_or_404(User, pk=pk, is_active=True)
        if has_passkey(edited_user):
            messages.error(request, f"{edited_user} already has a passkey. Reset it to get a new setup link.")
            return redirect("settings:user-edit", pk=pk)

        context = {"edited_user": edited_user, "link": setup_link(edited_user)}
        return TemplateResponse(request, "settings/user_setup_link.html", context)


@method_decorator(admin_required, name="dispatch")
class AboutView(View):
    def get(self, request, *args, **kwargs):
        latest = latest_version()
        context = {
            "version": settings.APP_VERSION,
            "latest_version": latest,
            "update_available": is_newer(latest, settings.APP_VERSION),
            "repository_url": settings.APP_REPOSITORY_URL,
            "issues_url": settings.APP_ISSUES_URL,
            "changelog_url": settings.APP_CHANGELOG_URL,
        }
        return TemplateResponse(request, "settings/about.html", context)


@method_decorator(admin_required, name="dispatch")
class UserResetPasskeysView(View):
    def post(self, request, pk, *args, **kwargs):
        if pk == request.user.pk:
            return redirect("users:account")

        edited_user = get_object_or_404(User, pk=pk)
        reset_passkeys(edited_user)
        return redirect("settings:user-setup-link", pk=pk)
