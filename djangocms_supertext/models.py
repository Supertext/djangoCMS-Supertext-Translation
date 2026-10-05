from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Translation(models.Model):
    """One translation of a page into a language (shown in the admin and in the translate dialog)."""

    STATUS_TRANSLATED = "translated"
    STATUS_SKIPPED = "skipped"
    STATUS_ERROR = "error"
    STATUS_CHOICES = [
        (STATUS_TRANSLATED, _("translated")),
        (STATUS_SKIPPED, _("skipped")),
        (STATUS_ERROR, _("error")),
    ]

    page = models.ForeignKey("cms.Page", on_delete=models.CASCADE, related_name="+", verbose_name=_("page"))
    source_language = models.CharField(_("from"), max_length=15)
    target_language = models.CharField(_("into"), max_length=15)
    status = models.CharField(_("status"), max_length=20, choices=STATUS_CHOICES)
    message = models.TextField(_("message"), blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, verbose_name=_("user"))
    created = models.DateTimeField(_("date"), auto_now_add=True)

    class Meta:
        verbose_name = _("Supertext translation")
        verbose_name_plural = _("Supertext translations")
        ordering = ["-created"]
        default_permissions = ("view",)
        permissions = [("translate", _("Can translate pages with Supertext"))]

    def __str__(self):
        return f"{self.page} {self.source_language} → {self.target_language}"
