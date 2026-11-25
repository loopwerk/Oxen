import base64

from django.db import models

from config.choices import country_choices, currency_choices


class SingletonModel(models.Model):
    """A model that only ever has one row, with pk 1."""

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls._default_manager.get_or_create(pk=1)
        return obj


class Company(SingletonModel):
    name = models.CharField(max_length=255)
    logo_data = models.BinaryField(null=True, blank=True)
    logo_type = models.CharField(max_length=50, blank=True)
    address_line_1 = models.CharField(max_length=255, verbose_name="Line 1")
    address_line_2 = models.CharField(max_length=255, blank=True, verbose_name="Line 2")
    address_postal_code = models.CharField(max_length=10, verbose_name="Postal Code")
    address_city = models.CharField(max_length=255, verbose_name="City")
    address_country = models.CharField(max_length=2, choices=country_choices, verbose_name="Country")
    vat_number = models.CharField(max_length=50, blank=True)
    company_details = models.TextField(blank=True, verbose_name="Registration and bank details")
    default_currency = models.CharField(max_length=3, choices=currency_choices)
    default_tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="Tax rate (%)")
    default_terms_days = models.PositiveSmallIntegerField(default=30)

    class Meta:
        verbose_name_plural = "company"

    def __str__(self):
        return self.name or "Company"

    @property
    def logo_data_uri(self):
        if not self.logo_data:
            return ""
        return f"data:{self.logo_type};base64,{base64.b64encode(bytes(self.logo_data)).decode()}"


class UpdateCheck(SingletonModel):
    latest_version = models.CharField(max_length=50, blank=True)
    checked_at = models.DateTimeField(null=True, blank=True)
    dismissed_version = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return self.latest_version or "Update check"
