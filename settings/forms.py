import io
from xml.etree import ElementTree

from django import forms
from PIL import Image

from .models import Company

MAX_LOGO_SIZE = 1024 * 1024
PILLOW_TYPES = {"PNG": "image/png", "JPEG": "image/jpeg", "WEBP": "image/webp"}
SVG_TAGS = {"svg", "{http://www.w3.org/2000/svg}svg"}


def _raster_type(data):
    try:
        with Image.open(io.BytesIO(data)) as image:
            image.verify()
            return PILLOW_TYPES.get(image.format or "")
    except OSError, SyntaxError, ValueError, Image.DecompressionBombError:
        return None


def _is_svg(data):
    try:
        return ElementTree.fromstring(data).tag in SVG_TAGS
    except ElementTree.ParseError:
        return False


def _logo_type(data):
    """The MIME type of an uploaded logo, judged by its content, or None if it's not an image we accept."""
    return _raster_type(data) or ("image/svg+xml" if _is_svg(data) else None)


class CompanyForm(forms.ModelForm):
    logo = forms.FileField(
        required=False,
        help_text="PNG, JPEG, WebP or SVG, at most 1 MB.",
        widget=forms.FileInput(attrs={"accept": "image/png,image/jpeg,image/webp,image/svg+xml"}),
    )

    remove_logo = forms.BooleanField(required=False, label="Remove the current logo")

    field_order = ["name", "logo", "remove_logo"]

    class Meta:
        model = Company
        fields = [
            "name",
            "address_line_1",
            "address_line_2",
            "address_postal_code",
            "address_city",
            "address_country",
            "vat_number",
            "company_details",
            "default_currency",
            "default_tax_rate",
            "default_terms_days",
        ]
        labels = {
            "name": "Company name",
            "vat_number": "VAT number",
            "default_tax_rate": "Default tax rate (%)",
            "default_terms_days": "Default payment terms (days)",
        }
        help_texts = {
            "company_details": "Shown under your address on invoices.",
        }
        widgets = {
            "company_details": forms.Textarea(
                attrs={"rows": 4, "placeholder": "Company number: 12345678\nBank: Example Bank\nAccount: 0123456789"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.logo_data:
            del self.fields["remove_logo"]

    def clean_logo(self):
        upload = self.cleaned_data["logo"]
        if not upload:
            return None
        if upload.size > MAX_LOGO_SIZE:
            raise forms.ValidationError("The logo can be at most 1 MB.")

        data = upload.read()
        mime_type = _logo_type(data)
        if not mime_type:
            raise forms.ValidationError("Upload a PNG, JPEG, WebP or SVG image.")
        return data, mime_type

    def save(self, commit=True):
        company = super().save(commit=False)
        if self.cleaned_data.get("logo"):
            company.logo_data, company.logo_type = self.cleaned_data["logo"]
        elif self.cleaned_data.get("remove_logo"):
            company.logo_data, company.logo_type = None, ""
        if commit:
            company.save()
        return company
