from django.urls import path

from .views import (
    ChooseClientView,
    ChooseHoursView,
    InvoiceCreateView,
    InvoiceDeleteView,
    InvoiceDetailView,
    InvoiceEditView,
    InvoiceFromHoursView,
    InvoiceListView,
    InvoiceMarkPaidView,
    InvoiceMarkUnpaidView,
    InvoicePdfView,
)

app_name = "invoices"

urlpatterns = [
    path("", InvoiceListView.as_view(), name="index"),
    path("create/", ChooseClientView.as_view(), name="choose-client"),
    path("create/<int:client_id>/", InvoiceCreateView.as_view(), name="create"),
    path("create/<int:client_id>/hours/", ChooseHoursView.as_view(), name="choose-hours"),
    path("create/<int:client_id>/from-hours/", InvoiceFromHoursView.as_view(), name="create-from-hours"),
    path("<int:pk>/", InvoiceDetailView.as_view(), name="detail"),
    path("<int:pk>/edit/", InvoiceEditView.as_view(), name="edit"),
    path("<int:pk>/delete/", InvoiceDeleteView.as_view(), name="delete"),
    path("<int:pk>/pdf/", InvoicePdfView.as_view(), name="pdf"),
    path("<int:pk>/paid/", InvoiceMarkPaidView.as_view(), name="mark-paid"),
    path("<int:pk>/unpaid/", InvoiceMarkUnpaidView.as_view(), name="mark-unpaid"),
]
