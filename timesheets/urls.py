from datetime import date

from django.urls import path, register_converter

from .views import WeekView


class DateConverter:
    regex = r"\d{4}-\d{2}-\d{2}"

    def to_python(self, value):
        return date.fromisoformat(value)

    def to_url(self, value):
        return value.isoformat()


register_converter(DateConverter, "date")

app_name = "timesheets"

urlpatterns = [
    path("", WeekView.as_view(), name="index"),
    path("<date:day>/", WeekView.as_view(), name="week"),
]
