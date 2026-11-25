from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import models

from clients.models import Project


class UserManager(BaseUserManager["User"]):
    def create_user(self, username, name="", is_admin=False):
        user = self.model(username=username, name=name, is_admin=is_admin)
        user.set_unusable_password()
        user.save(using=self._db)
        return user


class User(AbstractBaseUser):
    username = models.CharField(max_length=150, unique=True, validators=[UnicodeUsernameValidator()])
    name = models.CharField(max_length=150, blank=True)
    is_admin = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    projects = models.ManyToManyField("clients.Project", blank=True, related_name="users")

    objects = UserManager()

    USERNAME_FIELD = "username"

    def __str__(self):
        return self.name or self.username

    def accessible_projects(self):
        if self.is_admin:
            return Project.objects.all()
        return self.projects.all()
