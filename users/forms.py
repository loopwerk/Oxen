from typing import cast

from django import forms

from clients.models import Project

from .models import User


class LoginForm(forms.Form):
    username = forms.CharField(required=False, widget=forms.TextInput(attrs={"autocomplete": "username"}))
    next = forms.CharField(required=False, widget=forms.HiddenInput)


class AccountForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["name"]


class ProjectsField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, project):
        return f"{project.client} – {project.name}"


class UserForm(forms.ModelForm):
    projects = ProjectsField(
        queryset=Project.objects.filter(archived=False, client__archived=False)
        .select_related("client")
        .order_by("client__name", "name"),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text="The projects this user can track time on. Admins have access to every project.",
    )

    class Meta:
        model = User
        fields = ["username", "name", "is_admin", "is_active", "projects"]
        labels = {
            "is_admin": "Admin",
            "is_active": "Active",
        }
        help_texts = {
            "is_admin": "Admins can do everything. Other users only track their own time.",
            "is_active": "Inactive users can't log in.",
        }

    def clean_projects(self):
        # Archived projects aren't shown, so saving keeps the user's assignments to them
        projects = self.cleaned_data["projects"]
        if not self.instance.pk:
            return projects
        hidden = self.instance.projects.exclude(pk__in=cast(ProjectsField, self.fields["projects"]).queryset)
        return [*projects, *hidden]


class UserCreateForm(UserForm):
    class Meta(UserForm.Meta):
        fields = ["username", "name", "is_admin", "projects"]


class UserEditForm(UserForm):
    class Meta(UserForm.Meta):
        fields = ["name", "is_admin", "is_active", "projects"]
