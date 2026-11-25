from django.contrib.auth.views import LogoutView
from django.urls import path

from .views import AccountView, LoginView, PasskeySetupView, SetupLinkView

app_name = "users"

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("account/", AccountView.as_view(), name="account"),
    path("setup/<uidb64>/<token>/", SetupLinkView.as_view(), name="setup"),
    path("setup/passkey/", PasskeySetupView.as_view(), name="passkey"),
]
