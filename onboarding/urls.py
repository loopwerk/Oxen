from django.urls import path

from .views import AccountView, CompanyView

app_name = "onboarding"

urlpatterns = [
    path("", AccountView.as_view(), name="account"),
    path("company/", CompanyView.as_view(), name="company"),
]
