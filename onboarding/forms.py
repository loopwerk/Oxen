from django import forms
from django.conf import settings
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.utils.crypto import constant_time_compare


class SetupForm(forms.Form):
    token = forms.CharField(
        label="Setup token",
        widget=forms.TextInput(attrs={"autocomplete": "off"}),
    )
    username = forms.CharField(
        max_length=150,
        validators=[UnicodeUsernameValidator()],
        widget=forms.TextInput(attrs={"autocomplete": "username"}),
    )

    def clean_token(self):
        token = self.cleaned_data["token"]
        if not settings.SETUP_TOKEN or not constant_time_compare(token, settings.SETUP_TOKEN):
            raise forms.ValidationError("That's not the setup token.")
        return token
