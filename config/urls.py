from django.urls import include, path

urlpatterns = [
    path("", include("timesheets.urls")),
    path("invoices/", include("invoices.urls")),
    path("clients/", include("clients.urls")),
    path("settings/", include("settings.urls")),
    path("users/", include("users.urls")),
    path("setup/", include("onboarding.urls")),
    path("webauthn/", include("django_otp_webauthn.urls", namespace="otp_webauthn")),
    path("__reload__/", include("django_browser_reload.urls")),
]
