from django.forms.renderers import TemplatesSetting


class FormRenderer(TemplatesSetting):
    form_template_name = "forms/form.html"
    field_template_name = "forms/field.html"
