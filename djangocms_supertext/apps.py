from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class SupertextConfig(AppConfig):
    name = "djangocms_supertext"
    verbose_name = _("Supertext")
    default_auto_field = "django.db.models.BigAutoField"
