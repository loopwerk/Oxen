from django.contrib.auth import login
from django.contrib.auth.decorators import login_not_required
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.utils.decorators import method_decorator
from django.views import View

from settings.forms import CompanyForm
from settings.models import Company
from users.models import User

from .forms import SetupForm
from .middleware import setup_done


@method_decorator(login_not_required, name="dispatch")
class AccountView(View):
    """Onboarding step 1: the setup token and a username, then a passkey."""

    def get(self, request, *args, **kwargs):
        if setup_done():
            return redirect("timesheets:index")

        if request.user.is_authenticated:
            return TemplateResponse(request, "onboarding/passkey.html")

        return TemplateResponse(request, "onboarding/account.html", {"form": SetupForm()})

    def post(self, request, *args, **kwargs):
        if setup_done():
            return redirect("timesheets:index")

        form = SetupForm(data=request.POST)
        if form.is_valid():
            user = User.objects.order_by("pk").first() or User()
            user.username = form.cleaned_data["username"]
            user.is_admin = True
            user.set_unusable_password()
            user.save()
            login(request, user)
            return redirect("onboarding:account")

        return TemplateResponse(request, "onboarding/account.html", {"form": form})


class CompanyView(View):
    """Onboarding step 2: company details and logo. Once filled in, they're edited in Settings."""

    def get(self, request, *args, **kwargs):
        company = Company.load()
        if company.name or not request.user.is_admin:
            return redirect("timesheets:index")

        form = CompanyForm(instance=company)
        return TemplateResponse(request, "onboarding/company.html", {"form": form})

    def post(self, request, *args, **kwargs):
        company = Company.load()
        if company.name or not request.user.is_admin:
            return redirect("timesheets:index")

        form = CompanyForm(data=request.POST, files=request.FILES, instance=company)
        if form.is_valid():
            form.save()
            return redirect("timesheets:index")

        return TemplateResponse(request, "onboarding/company.html", {"form": form})
