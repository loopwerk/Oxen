from django import forms

from .models import Client, Project


class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = [
            "name",
            "address_line_1",
            "address_line_2",
            "address_postal_code",
            "address_city",
            "address_country",
            "vat_number",
            "currency",
            "tax_rate",
            "terms_days",
        ]


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ["name", "hourly_rate"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["hourly_rate"].label = f"Hourly rate ({self.instance.client.currency})"
