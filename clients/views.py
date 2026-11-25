from decimal import Decimal

from django.contrib import messages
from django.db.models import Prefetch, Q, Sum
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.utils.decorators import method_decorator
from django.views import View

from settings.models import Company
from timesheets.models import TimeEntry
from users.decorators import admin_required

from .forms import ClientForm, ProjectForm
from .models import Client, Project
from .stats import hour_totals, invoiced_amounts, uninvoiced_amount


@method_decorator(admin_required, name="dispatch")
class ClientListView(View):
    """Active clients with their active projects, or with ?status=archived, what's archived."""

    def get(self, request, *args, **kwargs):
        archived = request.GET.get("status") == "archived"
        if archived:
            # An archived project of an active client is listed under that client.
            clients = Client.objects.filter(Q(archived=True) | Q(projects__archived=True)).distinct()
            projects = Project.objects.filter(Q(archived=True) | Q(client__archived=True))
        else:
            clients = Client.objects.filter(archived=False)
            projects = Project.objects.filter(archived=False)

        clients = clients.prefetch_related(Prefetch("projects", queryset=projects, to_attr="listed_projects"))
        context = {"clients": clients, "archived": archived}

        if not archived and not clients:
            context["all_archived"] = Client.objects.exists()

        return TemplateResponse(request, "clients/index.html", context)


@method_decorator(admin_required, name="dispatch")
class ClientCreateView(View):
    def get(self, request, *args, **kwargs):
        company = Company.load()
        form = ClientForm(
            initial={
                "address_country": company.address_country,
                "currency": company.default_currency,
                "tax_rate": company.default_tax_rate,
                "terms_days": company.default_terms_days,
            }
        )
        return TemplateResponse(request, "clients/client_form.html", {"form": form})

    def post(self, request, *args, **kwargs):
        form = ClientForm(data=request.POST)
        if form.is_valid():
            form.save()
            return redirect("clients:index")

        return TemplateResponse(request, "clients/client_form.html", {"form": form})


@method_decorator(admin_required, name="dispatch")
class ClientDetailView(View):
    def get(self, request, pk, *args, **kwargs):
        client = get_object_or_404(Client, pk=pk)
        entries = TimeEntry.objects.filter(project__client=client)
        projects = client.projects.annotate(
            uninvoiced=Sum("time_entries__minutes", filter=Q(time_entries__invoice_line__isnull=True), default=0)
        )

        # Without any rate there's no amount to show, only hours.
        rated = [(p.uninvoiced, p.hourly_rate) for p in projects if p.hourly_rate is not None]
        amount = None
        if rated:
            amount = sum((uninvoiced_amount(minutes, rate, client.currency) for minutes, rate in rated), Decimal(0))

        context = {
            "client": client,
            "currency": client.currency,
            "hours": hour_totals(entries),
            "invoiced_amounts": invoiced_amounts(entries),
            "uninvoiced_amount": amount,
            "unrated_projects": [p for p in projects if p.hourly_rate is None and p.uninvoiced],
            "can_invoice": not client.archived and any(p.uninvoiced and not p.archived for p in projects),
        }
        return TemplateResponse(request, "clients/client_detail.html", context)


@method_decorator(admin_required, name="dispatch")
class ClientEditView(View):
    def get(self, request, pk, *args, **kwargs):
        client = get_object_or_404(Client, pk=pk)
        form = ClientForm(instance=client)
        return TemplateResponse(request, "clients/client_form.html", {"form": form, "client": client})

    def post(self, request, pk, *args, **kwargs):
        client = get_object_or_404(Client, pk=pk)
        form = ClientForm(data=request.POST, instance=client)
        if form.is_valid():
            form.save()
            messages.success(request, f"{client} is saved.")
            return redirect("clients:client", pk=client.pk)

        return TemplateResponse(request, "clients/client_form.html", {"form": form, "client": client})


@method_decorator(admin_required, name="dispatch")
class ClientArchiveView(View):
    def post(self, request, pk, *args, **kwargs):
        client = get_object_or_404(Client, pk=pk)
        client.archived = True
        client.save(update_fields=["archived"])
        messages.success(request, f"{client} is archived.")
        return redirect("clients:client", pk=client.pk)


@method_decorator(admin_required, name="dispatch")
class ClientUnarchiveView(View):
    def post(self, request, pk, *args, **kwargs):
        client = get_object_or_404(Client, pk=pk)
        client.archived = False
        client.save(update_fields=["archived"])
        messages.success(request, f"{client} is unarchived.")
        return redirect("clients:client", pk=client.pk)


@method_decorator(admin_required, name="dispatch")
class ProjectCreateView(View):
    def get(self, request, client_id, *args, **kwargs):
        client = get_object_or_404(Client, pk=client_id, archived=False)
        form = ProjectForm(instance=Project(client=client))
        return TemplateResponse(request, "clients/project_form.html", {"form": form, "client": client})

    def post(self, request, client_id, *args, **kwargs):
        client = get_object_or_404(Client, pk=client_id, archived=False)
        form = ProjectForm(data=request.POST, instance=Project(client=client))
        if form.is_valid():
            form.save()
            return redirect("clients:index")

        return TemplateResponse(request, "clients/project_form.html", {"form": form, "client": client})


@method_decorator(admin_required, name="dispatch")
class ProjectDetailView(View):
    def get(self, request, pk, *args, **kwargs):
        project = get_object_or_404(Project.objects.select_related("client"), pk=pk)
        currency = project.client.currency
        entries = project.time_entries.all()
        hours = hour_totals(entries)
        context = {
            "project": project,
            "currency": currency,
            "hours": hours,
            "invoiced_amounts": invoiced_amounts(entries),
            "uninvoiced_amount": (
                uninvoiced_amount(hours["uninvoiced"], project.hourly_rate, currency)
                if project.hourly_rate is not None
                else None
            ),
            "can_invoice": hours["uninvoiced"] and not project.archived and not project.client.archived,
        }
        return TemplateResponse(request, "clients/project_detail.html", context)


@method_decorator(admin_required, name="dispatch")
class ProjectEditView(View):
    def get(self, request, pk, *args, **kwargs):
        project = get_object_or_404(Project.objects.select_related("client"), pk=pk)
        form = ProjectForm(instance=project)
        return TemplateResponse(request, "clients/project_form.html", {"form": form, "project": project})

    def post(self, request, pk, *args, **kwargs):
        project = get_object_or_404(Project.objects.select_related("client"), pk=pk)
        form = ProjectForm(data=request.POST, instance=project)
        if form.is_valid():
            form.save()
            messages.success(request, f"{project} is saved.")
            return redirect("clients:project", pk=project.pk)

        return TemplateResponse(request, "clients/project_form.html", {"form": form, "project": project})


@method_decorator(admin_required, name="dispatch")
class ProjectArchiveView(View):
    def post(self, request, pk, *args, **kwargs):
        project = get_object_or_404(Project, pk=pk)
        project.archived = True
        project.save(update_fields=["archived"])
        messages.success(request, f"{project} is archived.")
        return redirect("clients:project", pk=project.pk)


@method_decorator(admin_required, name="dispatch")
class ProjectUnarchiveView(View):
    def post(self, request, pk, *args, **kwargs):
        project = get_object_or_404(Project, pk=pk)
        project.archived = False
        project.save(update_fields=["archived"])
        messages.success(request, f"{project} is unarchived.")
        return redirect("clients:project", pk=project.pk)
