from django.urls import path

from .views import (
    AboutView,
    CompanySettingsView,
    SettingsView,
    UserCreateView,
    UserEditView,
    UserListView,
    UserResetPasskeysView,
    UserSetupLinkView,
)

app_name = "settings"

urlpatterns = [
    path("", SettingsView.as_view(), name="index"),
    path("company/", CompanySettingsView.as_view(), name="company"),
    path("users/", UserListView.as_view(), name="users"),
    path("users/create/", UserCreateView.as_view(), name="user-create"),
    path("users/<int:pk>/", UserEditView.as_view(), name="user-edit"),
    path("users/<int:pk>/setup-link/", UserSetupLinkView.as_view(), name="user-setup-link"),
    path("users/<int:pk>/reset-passkeys/", UserResetPasskeysView.as_view(), name="user-reset-passkeys"),
    path("about/", AboutView.as_view(), name="about"),
]
