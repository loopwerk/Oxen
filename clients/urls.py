from django.urls import path

from .views import (
    ClientArchiveView,
    ClientCreateView,
    ClientDetailView,
    ClientEditView,
    ClientListView,
    ClientUnarchiveView,
    ProjectArchiveView,
    ProjectCreateView,
    ProjectDetailView,
    ProjectEditView,
    ProjectUnarchiveView,
)

app_name = "clients"

urlpatterns = [
    path("", ClientListView.as_view(), name="index"),
    path("create/", ClientCreateView.as_view(), name="create"),
    path("<int:pk>/", ClientDetailView.as_view(), name="client"),
    path("<int:pk>/edit/", ClientEditView.as_view(), name="edit"),
    path("<int:pk>/archive/", ClientArchiveView.as_view(), name="archive"),
    path("<int:pk>/unarchive/", ClientUnarchiveView.as_view(), name="unarchive"),
    path("<int:client_id>/create-project/", ProjectCreateView.as_view(), name="create-project"),
    path("projects/<int:pk>/", ProjectDetailView.as_view(), name="project"),
    path("projects/<int:pk>/edit/", ProjectEditView.as_view(), name="edit-project"),
    path("projects/<int:pk>/archive/", ProjectArchiveView.as_view(), name="archive-project"),
    path("projects/<int:pk>/unarchive/", ProjectUnarchiveView.as_view(), name="unarchive-project"),
]
