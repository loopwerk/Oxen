from collections.abc import Iterator
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.core.exceptions import SuspiciousFileOperation
from django.template import Origin
from django.template.loaders.filesystem import Loader
from django.utils._os import safe_join


class AppLoader(Loader):
    """
    Finds "timesheets/week.html" in timesheets/templates/week.html,
    rather than timesheets/templates/timesheets/week.html.
    """

    def get_template_sources(self, template_name: str) -> Iterator[Origin]:
        app_label, _, rest = template_name.partition("/")
        if not rest:
            return
        try:
            app_path = Path(apps.get_app_config(app_label).path)
        except LookupError:
            return
        if app_path.parent != Path(settings.BASE_DIR):
            return
        try:
            name = safe_join(app_path / "templates", rest)
        except SuspiciousFileOperation:
            return
        yield Origin(name=name, template_name=template_name, loader=self)
