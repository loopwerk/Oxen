from datetime import timedelta

from django.contrib import messages
from django.db import transaction
from django.db.models import Exists, OuterRef, QuerySet, Sum
from django.http import HttpResponse, HttpResponseRedirect, QueryDict
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.http import content_disposition_header
from django.views import View
from django.views.decorators.clickjacking import xframe_options_sameorigin
from weasyprint import HTML

from clients.models import Client
from settings.models import Company
from timesheets.models import TimeEntry
from users.decorators import admin_required

from .forms import (
    ChooseClientForm,
    EditLineFormSet,
    ExtraLineFormSet,
    HourLineFormSet,
    HoursSelectionForm,
    InvoiceForm,
    InvoiceLineFormSet,
    MarkPaidForm,
)
from .models import Invoice, InvoiceLine, next_invoice_number


def _new_invoice_form(client: Client, subject: str = "") -> InvoiceForm:
    today = timezone.localdate()
    return InvoiceForm(
        initial={
            "number": next_invoice_number(today.year),
            "issue_date": today,
            "due_date": today + timedelta(days=client.terms_days),
            "subject": subject,
            "currency": client.currency,
            "tax_rate": client.tax_rate,
        }
    )


def _create_invoice(form: InvoiceForm, client: Client) -> Invoice:
    """Saves the invoice from a valid InvoiceForm. Only the very first invoice brings its own number."""
    invoice = form.save(commit=False)
    invoice.client = client
    if not invoice.number:
        invoice.number = next_invoice_number(invoice.issue_date.year)
    invoice.save()
    return invoice


def _back_to_choose_hours(client: Client, query: QueryDict) -> HttpResponseRedirect:
    """Step 2 again, with what was picked there, so it can show what's wrong with it."""
    url = reverse("invoices:choose-hours", kwargs={"client_id": client.pk})
    return redirect(f"{url}?{query.urlencode()}")


def _lines_marking_tracked(invoice: Invoice) -> QuerySet[InvoiceLine]:
    """Its lines, with `tracked` set on the ones from tracked hours."""
    return invoice.lines.annotate(tracked=Exists(TimeEntry.objects.filter(invoice_line=OuterRef("pk"))))


def _minutes_per_project(entries: QuerySet[TimeEntry]) -> dict[str, int]:
    """Keyed by project id as a string, the way a posted form value is."""
    totals = entries.order_by().values_list("project").annotate(Sum("minutes"))
    return {str(project): minutes for project, minutes in totals}


@method_decorator(admin_required, name="dispatch")
class InvoiceListView(View):
    """All invoices, or with ?status=open, overdue or paid, only those."""

    def get(self, request, *args, **kwargs):
        invoices = Invoice.objects.select_related("client").prefetch_related("lines")
        filters = Invoice.status_filters()
        status = request.GET.get("status")
        if status in filters:
            invoices = invoices.filter(filters[status])
        else:
            status = None
        clients = Client.objects.count()
        context = {"invoices": invoices, "clients": clients, "status": status}
        return TemplateResponse(request, "invoices/index.html", context)


@method_decorator(admin_required, name="dispatch")
class ChooseClientView(View):
    """New invoice, step 1: pick the client, and whether the invoice is from hours or free-form."""

    def get(self, request, *args, **kwargs):
        if "client" not in request.GET:
            return TemplateResponse(request, "invoices/choose_client.html", {"form": ChooseClientForm()})

        form = ChooseClientForm(data=request.GET)
        if form.is_valid():
            client = form.cleaned_data["client"]
            if request.GET.get("type") == "free-form":
                return redirect("invoices:create", client_id=client.pk)
            return redirect("invoices:choose-hours", client_id=client.pk)

        return TemplateResponse(request, "invoices/choose_client.html", {"form": form})


@method_decorator(admin_required, name="dispatch")
class InvoiceCreateView(View):
    """New invoice, step 2: a free-form invoice with lines of a quantity and a unit price."""

    def get(self, request, client_id, *args, **kwargs):
        client = get_object_or_404(Client, pk=client_id, archived=False)
        context = {"client": client, "form": _new_invoice_form(client), "formset": InvoiceLineFormSet()}
        return TemplateResponse(request, "invoices/invoice_form.html", context)

    def post(self, request, client_id, *args, **kwargs):
        client = get_object_or_404(Client, pk=client_id, archived=False)
        form = InvoiceForm(data=request.POST)
        formset = InvoiceLineFormSet(data=request.POST)

        if all([form.is_valid(), formset.is_valid()]):
            with transaction.atomic():
                invoice = _create_invoice(form, client)
                for position, line in enumerate(formset.save(commit=False), start=1):
                    line.invoice = invoice
                    line.position = position
                    line.save()

            return redirect("invoices:detail", pk=invoice.pk)

        context = {"client": client, "form": form, "formset": formset}
        return TemplateResponse(request, "invoices/invoice_form.html", context)


@method_decorator(admin_required, name="dispatch")
class ChooseHoursView(View):
    """New invoice from hours, step 2: pick the period and the projects."""

    def get(self, request, client_id, *args, **kwargs):
        client = get_object_or_404(Client, pk=client_id, archived=False)
        if "period" not in request.GET:
            form = HoursSelectionForm(client=client, initial={"period": "all"})
            # Coming from a project page, only that project is ticked.
            projects = form.uninvoiced_projects
            project_id = request.GET.get("project", "")
            chosen = list(projects.filter(pk=project_id)) if project_id.isdigit() else []
            form.initial["projects"] = chosen or list(projects)
            return TemplateResponse(request, "invoices/choose_hours.html", {"client": client, "form": form})

        form = HoursSelectionForm(data=request.GET, client=client)
        if form.is_valid():
            url = reverse("invoices:create-from-hours", kwargs={"client_id": client.pk})
            return redirect(f"{url}?{request.GET.urlencode()}")

        return TemplateResponse(request, "invoices/choose_hours.html", {"client": client, "form": form})


@method_decorator(admin_required, name="dispatch")
class InvoiceFromHoursView(View):
    """New invoice from hours, step 3: a line per project with its hours and hourly rate, plus any extra lines.

    The period and projects from step 2 stay in the query string, also when the form is posted.
    """

    def get(self, request, client_id, *args, **kwargs):
        client = get_object_or_404(Client, pk=client_id, archived=False)
        selection = HoursSelectionForm(data=request.GET, client=client)
        if not selection.is_valid():
            return _back_to_choose_hours(client, request.GET)

        projects = selection.cleaned_data["projects"]
        minutes = _minutes_per_project(selection.entries())
        hour_formset = HourLineFormSet(
            prefix="hours",
            initial=[
                {"project": project.pk, "description": project.name, "unit_price": project.hourly_rate}
                for project in projects
                if str(project.pk) in minutes
            ],
            form_kwargs={"projects": projects, "minutes": minutes},
        )
        period = selection.periods[selection.cleaned_data["period"]]
        context = {
            "client": client,
            "form": _new_invoice_form(client, subject=period.subject),
            "hour_formset": hour_formset,
            "formset": ExtraLineFormSet(),
        }
        return TemplateResponse(request, "invoices/invoice_form.html", context)

    def post(self, request, client_id, *args, **kwargs):
        client = get_object_or_404(Client, pk=client_id, archived=False)
        selection = HoursSelectionForm(data=request.GET, client=client)
        if not selection.is_valid():
            return _back_to_choose_hours(client, request.GET)

        entries = selection.entries()
        form = InvoiceForm(data=request.POST)
        hour_formset = HourLineFormSet(
            data=request.POST,
            prefix="hours",
            form_kwargs={"projects": selection.cleaned_data["projects"], "minutes": _minutes_per_project(entries)},
        )
        formset = ExtraLineFormSet(data=request.POST)

        if all([form.is_valid(), hour_formset.is_valid(), formset.is_valid()]):
            with transaction.atomic():
                invoice = _create_invoice(form, client)
                position = 0
                for hour_form in hour_formset:
                    # Counted again and locked, so a line always matches the hours linked to it.
                    project_entries = list(
                        entries.filter(project=hour_form.cleaned_data["project"]).select_for_update()
                    )
                    if not project_entries:
                        continue

                    position += 1
                    line = invoice.lines.create(
                        position=position,
                        description=hour_form.cleaned_data["description"],
                        minutes=sum(entry.minutes for entry in project_entries),
                        unit_price=hour_form.cleaned_data["unit_price"],
                    )
                    TimeEntry.objects.filter(pk__in=[entry.pk for entry in project_entries]).update(invoice_line=line)

                for line in formset.save(commit=False):
                    position += 1
                    line.invoice = invoice
                    line.position = position
                    line.save()

            return redirect("invoices:detail", pk=invoice.pk)

        context = {"client": client, "form": form, "hour_formset": hour_formset, "formset": formset}
        return TemplateResponse(request, "invoices/invoice_form.html", context)


@method_decorator(admin_required, name="dispatch")
class InvoiceDetailView(View):
    def get(self, request, pk, *args, **kwargs):
        invoice = get_object_or_404(Invoice.objects.select_related("client"), pk=pk)
        context = {
            "invoice": invoice,
            "paid_form": MarkPaidForm(initial={"paid_on": timezone.localdate()}),
            "tracked_minutes": TimeEntry.objects.filter(invoice_line__invoice=invoice).aggregate(
                minutes=Sum("minutes", default=0)
            )["minutes"],
        }
        return TemplateResponse(request, "invoices/detail.html", context)


@method_decorator(admin_required, name="dispatch")
class InvoiceEditView(View):
    def get(self, request, pk, *args, **kwargs):
        invoice = get_object_or_404(Invoice.objects.select_related("client"), pk=pk)
        context = {
            "invoice": invoice,
            "client": invoice.client,
            "form": InvoiceForm(instance=invoice),
            "formset": EditLineFormSet(queryset=_lines_marking_tracked(invoice)),
        }
        return TemplateResponse(request, "invoices/invoice_form.html", context)

    def post(self, request, pk, *args, **kwargs):
        invoice = get_object_or_404(Invoice.objects.select_related("client"), pk=pk)
        form = InvoiceForm(data=request.POST, instance=invoice)
        formset = EditLineFormSet(data=request.POST, queryset=_lines_marking_tracked(invoice))

        if all([form.is_valid(), formset.is_valid()]):
            with transaction.atomic():
                form.save()
                for line_form in formset.deleted_forms:
                    # A line from tracked hours releases them: their link to it is set to NULL.
                    line_form.instance.delete()

                kept = [
                    line_form
                    for line_form in formset.forms
                    if line_form not in formset.deleted_forms and (line_form.instance.pk or line_form.has_changed())
                ]
                for position, line_form in enumerate(kept, start=1):
                    line = line_form.save(commit=False)
                    line.invoice = invoice
                    line.position = position
                    line.save()

            messages.success(request, f"Invoice {invoice} is saved.")
            return redirect("invoices:detail", pk=invoice.pk)

        context = {"invoice": invoice, "client": invoice.client, "form": form, "formset": formset}
        return TemplateResponse(request, "invoices/invoice_form.html", context)


@method_decorator(admin_required, name="dispatch")
class InvoiceDeleteView(View):
    def post(self, request, pk, *args, **kwargs):
        invoice = get_object_or_404(Invoice, pk=pk)
        # Its lines go with it, which releases their hours.
        invoice.delete()
        messages.success(request, f"Invoice {invoice} is deleted.")
        return redirect("invoices:index")


@method_decorator(admin_required, name="dispatch")
class InvoiceMarkPaidView(View):
    def post(self, request, pk, *args, **kwargs):
        invoice = get_object_or_404(Invoice.objects.select_related("client"), pk=pk)
        paid_form = MarkPaidForm(data=request.POST)
        if paid_form.is_valid():
            invoice.paid_on = paid_form.cleaned_data["paid_on"]
            invoice.save(update_fields=["paid_on"])
            return redirect("invoices:detail", pk=invoice.pk)

        return TemplateResponse(request, "invoices/detail.html", {"invoice": invoice, "paid_form": paid_form})


@method_decorator(admin_required, name="dispatch")
class InvoiceMarkUnpaidView(View):
    def post(self, request, pk, *args, **kwargs):
        invoice = get_object_or_404(Invoice, pk=pk)
        invoice.paid_on = None
        invoice.save(update_fields=["paid_on"])
        return redirect("invoices:detail", pk=invoice.pk)


@method_decorator(admin_required, name="dispatch")
@method_decorator(xframe_options_sameorigin, name="dispatch")
class InvoicePdfView(View):
    """The invoice as PDF: shown inline on the invoice page, or downloaded with ?download."""

    def get(self, request, pk, *args, **kwargs):
        invoice = get_object_or_404(Invoice.objects.select_related("client"), pk=pk)
        company = Company.load()
        context = {
            "invoice": invoice,
            "client": invoice.client,
            "company": company,
            "terms_days": (invoice.due_date - invoice.issue_date).days,
            "show_client_country": invoice.client.address_country != company.address_country,
        }
        pdf = HTML(string=render_to_string("invoices/pdf.html", context)).write_pdf()

        response = HttpResponse(pdf, content_type="application/pdf")
        disposition = content_disposition_header(
            as_attachment="download" in request.GET,
            filename=f"INVOICE_{invoice.number}_{company.name}.pdf",
        )
        assert disposition is not None  # Only None without a filename.
        response["Content-Disposition"] = disposition
        return response
