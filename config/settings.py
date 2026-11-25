import os
import tomllib
from pathlib import Path
from urllib.parse import urlsplit

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(str(BASE_DIR / "config" / ".env"))

# GENERAL CONFIGURATION
# ------------------------------------------------------------------------------

DEBUG = os.getenv("DEBUG", default="").lower() == "true"
SECRET_KEY = os.getenv("SECRET_KEY")
SETUP_TOKEN = os.getenv("SETUP_TOKEN")
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
AUTH_USER_MODEL = "users.User"
UPDATE_CHECK = not DEBUG and os.getenv("UPDATE_CHECK", default="true").lower() != "false"

if not SECRET_KEY or not SETUP_TOKEN:
    raise ImproperlyConfigured("Set the SECRET_KEY and SETUP_TOKEN environment variables.")

with (BASE_DIR / "pyproject.toml").open("rb") as pyproject:
    project = tomllib.load(pyproject)["project"]
    APP_VERSION = project["version"]
    APP_REPOSITORY_URL = project["urls"]["Repository"].removesuffix(".git")
    APP_ISSUES_URL = project["urls"]["Issues"]
    APP_CHANGELOG_URL = project["urls"]["Changelog"]


# The public URL, such as https://hours.example.com.
# It also sets the allowed host, the CSRF origin and the passkey domain.
APP_URL = os.getenv("APP_URL", default="http://localhost:8000").rstrip("/")
ALLOWED_HOSTS = [urlsplit(APP_URL).hostname, "localhost", "127.0.0.1"]
CSRF_TRUSTED_ORIGINS = [APP_URL]
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = CSRF_COOKIE_SECURE = APP_URL.startswith("https://")

# DATABASE CONFIGURATION
# ------------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB"),
        "USER": os.getenv("POSTGRES_USER"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD"),
        "HOST": os.getenv("POSTGRES_HOST"),
        "PORT": "5432",
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# APP CONFIGURATION
# ------------------------------------------------------------------------------

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.forms",
    "django_tailwind_cli",
    "django_browser_reload",
    "django_otp",
    "django_otp_webauthn",
    "invoices",
    "onboarding",
    "clients",
    "settings",
    "timesheets",
    "users",
]

# MIDDLEWARE CONFIGURATION
# ------------------------------------------------------------------------------

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django_otp.middleware.OTPMiddleware",
    "onboarding.middleware.OnboardingMiddleware",
    "users.middleware.LoginRequiredMiddleware",
    "settings.middleware.UpdateCheckMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_browser_reload.middleware.BrowserReloadMiddleware",
]

# TEMPLATE CONFIGURATION
# ------------------------------------------------------------------------------

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "OPTIONS": {
            "loaders": [
                (
                    "django.template.loaders.cached.Loader",
                    [
                        "django.template.loaders.filesystem.Loader",
                        "config.template_loaders.AppLoader",
                        "django.template.loaders.app_directories.Loader",
                    ],
                )
            ],
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

FORM_RENDERER = "config.forms.FormRenderer"

# STATIC & MEDIA FILE CONFIGURATION
# ------------------------------------------------------------------------------

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "static_root"

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
        if DEBUG
        else "django.contrib.staticfiles.storage.ManifestStaticFilesStorage",
    },
}

# INTERNATIONALIZATION
# ------------------------------------------------------------------------------

LANGUAGE_CODE = "en-us"
TIME_ZONE = os.getenv("TIME_ZONE", default="UTC")
USE_I18N = False
USE_TZ = True

# TAILWIND
# ------------------------------------------------------------------------------

TAILWIND_CLI_VERSION = "4.3.5"
TAILWIND_CLI_SRC_CSS = "config/source.css"

# AUTHENTICATION
# ------------------------------------------------------------------------------

AUTHENTICATION_BACKENDS = ["django_otp_webauthn.backends.WebAuthnBackend"]
LOGIN_URL = "users:login"
LOGIN_REDIRECT_URL = "timesheets:index"
LOGOUT_REDIRECT_URL = "users:login"
OTP_WEBAUTHN_RP_ID = urlsplit(APP_URL).hostname
OTP_WEBAUTHN_RP_NAME = "Oxen"
OTP_WEBAUTHN_ALLOWED_ORIGINS = [APP_URL]

# How long setup links are valid for
PASSWORD_RESET_TIMEOUT = 60 * 60
