from django.db import models

from config.choices import country_choices, currency_choices


class Client(models.Model):
    name = models.CharField(max_length=255)
    address_line_1 = models.CharField(max_length=255, verbose_name="Line 1")
    address_line_2 = models.CharField(max_length=255, blank=True, verbose_name="Line 2")
    address_postal_code = models.CharField(max_length=10, verbose_name="Postal Code")
    address_city = models.CharField(max_length=255, verbose_name="City")
    address_country = models.CharField(max_length=2, choices=country_choices, verbose_name="Country")
    vat_number = models.CharField(max_length=50, blank=True)
    currency = models.CharField(max_length=3, choices=currency_choices)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="Tax rate (%)")
    terms_days = models.PositiveSmallIntegerField()
    archived = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Project(models.Model):
    name = models.CharField(max_length=255)
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name="projects")
    hourly_rate = models.DecimalField(null=True, blank=True, max_digits=10, decimal_places=2)
    archived = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
