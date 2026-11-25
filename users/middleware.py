from django.contrib.auth.middleware import LoginRequiredMiddleware as BaseLoginRequiredMiddleware

# Other packages' endpoints that must work logged out, but can't be decorated with @login_not_required.
PUBLIC_NAMESPACES = {"otp_webauthn", "django_browser_reload"}


class LoginRequiredMiddleware(BaseLoginRequiredMiddleware):
    def process_view(self, request, view_func, view_args, view_kwargs):
        if request.resolver_match.namespace in PUBLIC_NAMESPACES:
            return None
        return super().process_view(request, view_func, view_args, view_kwargs)
