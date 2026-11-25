import re
from typing import cast

from django import forms
from django.db.models import Sum
from django.utils import timezone

from clients.models import Client, Project
from timesheets.hours import format_hours, parse_hours
from timesheets.models import TimeEntry

from .models import Invoice, InvoiceLine
from .periods import periods

NUMBER_FORMAT = re.compile(r"^\d{4}-\d{4}$")


class ChooseClientForm(forms.Form):
    client = forms.ModelChoiceField(queryset=Client.objects.filter(archived=False))


class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = ["number", "issue_date", "due_date", "subject", "currency", "tax_rate"]
        widgets = {
            "issue_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "due_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only the very first invoice gets to pick its number. After that, numbers are assigned automatically.
        if Invoice.objects.exists():
            del self.fields["number"]

    def clean(self):
        super().clean()
        cleaned_data = self.cleaned_data
        number = cleaned_data.get("number")
        issue_date = cleaned_data.get("issue_date")
        if not number or not issue_date:
            return cleaned_data

        if not NUMBER_FORMAT.match(number) or number[:4] != str(issue_date.year):
            self.add_error("number", f"Use the format {issue_date.year}-0001, with the year of the issue date.")
        return cleaned_data


class MarkPaidForm(forms.Form):
    paid_on = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date", "aria-label": "Paid on"}, format="%Y-%m-%d"),
    )


QUANTITY = forms.DecimalField(max_digits=10, decimal_places=2)


class InvoiceLineForm(forms.ModelForm):
    # Hours like 5:30 make it an hour line, the same as a line from tracked hours. Anything else is a quantity.
    quantity = forms.CharField(initial="1")
    minutes = None

    class Meta:
        model = InvoiceLine
        fields = ["description", "quantity", "unit_price"]
        widgets = {
            "description": forms.TextInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.minutes is not None:
            self.initial["quantity"] = format_hours(self.instance.minutes)

        # A line from tracked hours gets its hours from the time entries.
        if getattr(self.instance, "tracked", False):
            self.fields["quantity"].disabled = True

    def clean_quantity(self):
        value = self.cleaned_data["quantity"]
        if ":" not in value:
            return QUANTITY.clean(value)

        try:
            self.minutes = parse_hours(value)
        except ValueError:
            raise forms.ValidationError("Use hours like 5:30.") from None
        return None

    def save(self, commit=True):
        self.instance.minutes = self.minutes
        return super().save(commit)


class BaseInvoiceLineFormSet(forms.BaseModelFormSet):
    default_error_messages = {
        **forms.BaseModelFormSet.default_error_messages,
        "too_few_forms": "An invoice needs at least one line.",
    }

    def __init__(self, *args, **kwargs):
        # Only new lines; without this, a model formset starts with every line in the database.
        kwargs.setdefault("queryset", InvoiceLine.objects.none())
        super().__init__(*args, **kwargs)

    def add_fields(self, form, index):
        super().add_fields(form, index)
        if "DELETE" in form.fields:
            form.fields["DELETE"].widget.attrs["aria-label"] = f"Remove line {index + 1}"


InvoiceLineFormSet = forms.modelformset_factory(
    InvoiceLine,
    form=InvoiceLineForm,
    formset=BaseInvoiceLineFormSet,
    extra=4,
    min_num=1,
    validate_min=True,
)


EditLineFormSet = forms.modelformset_factory(
    InvoiceLine,
    form=InvoiceLineForm,
    formset=BaseInvoiceLineFormSet,
    extra=2,
    min_num=1,
    validate_min=True,
    can_delete=True,
    can_delete_extra=False,
)


ExtraLineFormSet = forms.modelformset_factory(
    InvoiceLine,
    form=InvoiceLineForm,
    formset=BaseInvoiceLineFormSet,
    extra=2,
)


class PeriodSelect(forms.RadioSelect):
    """Radio buttons that can disable some of their choices."""

    disabled_values = ()

    def create_option(self, *args, **kwargs):
        option = super().create_option(*args, **kwargs)
        if option["value"] in self.disabled_values:
            option["attrs"]["disabled"] = True
        return option


class HoursSelectionForm(forms.Form):
    """Which of a client's uninvoiced hours go on an invoice."""

    period = forms.ChoiceField(label="Hours", widget=PeriodSelect)
    projects = forms.ModelMultipleChoiceField(
        queryset=Project.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        error_messages={"required": "Tick at least one project."},
    )

    def __init__(self, *args, client, **kwargs):
        super().__init__(*args, **kwargs)
        self.periods = periods(timezone.localdate())
        uninvoiced = TimeEntry.objects.filter(
            project__client=client, project__archived=False, invoice_line__isnull=True
        )

        # Each period shows its hours for all projects: without JavaScript, they can't follow the ticked ones.
        totals = uninvoiced.aggregate(
            **{key: Sum("minutes", filter=period.q(), default=0) for key, period in self.periods.items()}
        )
        period_field = cast(forms.ChoiceField, self.fields["period"])
        period_field.choices = [
            (key, f"{period.label} · {format_hours(totals[key])}") for key, period in self.periods.items()
        ]
        period_field.widget.disabled_values = {key for key, minutes in totals.items() if not minutes}
        self.uninvoiced_projects = client.projects.filter(pk__in=uninvoiced.values("project"))
        projects_field = cast(forms.ModelMultipleChoiceField, self.fields["projects"])
        projects_field.queryset = self.uninvoiced_projects

    def clean(self):
        super().clean()
        cleaned_data = self.cleaned_data
        if "period" in cleaned_data and "projects" in cleaned_data and not self.entries().exists():
            raise forms.ValidationError("There are no uninvoiced hours for these projects in that period.")
        return cleaned_data

    def entries(self):
        """The uninvoiced hours this selection covers."""
        period = self.periods[self.cleaned_data["period"]]
        return TimeEntry.objects.filter(
            period.q(),
            project__in=self.cleaned_data["projects"],
            invoice_line__isnull=True,
        )


class HourLineForm(forms.Form):
    """A line with a project's hours. Saving the invoice counts the hours again, so they're not a field."""

    project = forms.ModelChoiceField(queryset=Project.objects.none(), widget=forms.HiddenInput)
    description = forms.CharField(widget=forms.TextInput)
    unit_price = forms.DecimalField(max_digits=10, decimal_places=2)

    def __init__(self, *args, projects, minutes, **kwargs):
        super().__init__(*args, **kwargs)
        cast(forms.ModelChoiceField, self.fields["project"]).queryset = projects
        self.minutes = minutes.get(str(self["project"].value()), 0)


HourLineFormSet = forms.formset_factory(HourLineForm, extra=0)
