"""
Admin: the list of Supertext translations, the translate dialog (opened from the django CMS
toolbar) and the Supertext settings page with "Test connection".

    /admin/djangocms_supertext/translation/                    list (view permission)
    /admin/djangocms_supertext/translation/page/<page_id>/     translate dialog
    /admin/djangocms_supertext/translation/settings/           settings and Test connection (superusers)
"""

from __future__ import annotations

import re

from django import forms
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy

from . import __version__, conf, translator
from .client import SupertextError
from .translator import localized
from .models import Translation

PERMISSION = "djangocms_supertext.translate"
RELEASES_URL = "https://github.com/Supertext/djangoCMS-Supertext-Translation/releases/tag/v{version}"


def plugin_version() -> dict:
    """The installed package version (``djangocms_supertext.__version__``) and, for a release
    (X.Y.Z), the link to its GitHub release."""
    version = __version__
    url = RELEASES_URL.format(version=version) if re.fullmatch(r"\d+\.\d+\.\d+", version) else ""
    return {"number": version, "url": url}


class TranslateForm(forms.Form):
    source = forms.ChoiceField(label=gettext_lazy("From"))
    targets = forms.MultipleChoiceField(label=gettext_lazy("Into"), widget=forms.CheckboxSelectMultiple, required=True)
    overwrite = forms.BooleanField(
        label=gettext_lazy("Overwrite existing translations"),
        required=False,
        help_text=gettext_lazy(
            "Languages that already exist are replaced by a new translation of the source: the page "
            "fields and all plugins. Changes made in those languages are lost. Leave this off to "
            "translate only the missing languages."
        ),
    )

    def __init__(self, *args, languages: list[dict], source: str, **kwargs):
        super().__init__(*args, **kwargs)
        existing = [lang for lang in languages if lang["exists"]]
        self.fields["source"].choices = [(lang["code"], lang["name"]) for lang in existing]
        self.fields["source"].initial = source
        self.fields["targets"].choices = [(lang["code"], lang["name"]) for lang in languages]
        self.fields["targets"].initial = [lang["code"] for lang in languages if not lang["exists"] and lang["code"] != source]


@admin.register(Translation)
class TranslationAdmin(admin.ModelAdmin):
    list_display = ("created", "page", "source_language", "target_language", "status", "user", "message")
    list_filter = ("status", "target_language")
    search_fields = ("page__pagecontent_set__title", "message")
    date_hierarchy = "created"
    change_list_template = "djangocms_supertext/admin/change_list.html"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def get_urls(self):
        return [
            path("page/<int:page_id>/", self.admin_site.admin_view(self.translate_view), name="djangocms_supertext_translate"),
            path("settings/", self.admin_site.admin_view(self.settings_view), name="djangocms_supertext_settings"),
        ] + super().get_urls()

    # -- translate dialog ---------------------------------------------------------------------

    def translate_view(self, request, page_id: int):
        from cms.models import Page

        if not request.user.has_perm(PERMISSION):
            raise PermissionDenied
        page = get_object_or_404(Page, pk=page_id)
        if not page.has_change_permission(request.user):
            raise PermissionDenied
        options = conf.load()
        languages = translator.describe(page)
        source = request.GET.get("language") or request.POST.get("source") or next((lang["code"] for lang in languages if lang["exists"]), "")
        form = TranslateForm(request.POST or None, languages=languages, source=source)
        results = None

        if request.method == "POST" and form.is_valid():
            try:
                results = translator.translate_page(
                    page,
                    form.cleaned_data["source"],
                    form.cleaned_data["targets"],
                    overwrite=form.cleaned_data["overwrite"],
                    user=request.user,
                    options=options,
                )
            except SupertextError as error:
                form.add_error(None, localized(error))
            else:
                # Start over with the new state: nothing ticked that is translated now.
                languages = translator.describe(page)
                source = form.cleaned_data["source"]
                form = TranslateForm(languages=languages, source=source)

        names = {lang["code"]: lang["name"] for lang in languages}
        context = {
            **self.admin_site.each_context(request),
            "title": _("Translate with Supertext"),
            "page": page,
            "form": form,
            "languages": languages,
            "source": source,
            "configured": bool(options.api_key),
            "signup_url": conf.SIGNUP_URL,
            "api_key_url": conf.API_KEY_URL,
            "results": [
                {"result": r, "name": names.get(r.language, r.language), "url": _edit_url(page, r.language)}
                for r in results or []
            ],
            "is_popup": True,
        }
        return TemplateResponse(request, "djangocms_supertext/translate.html", context)

    # -- settings ------------------------------------------------------------------------------

    def settings_view(self, request):
        if not request.user.is_superuser:
            raise PermissionDenied
        from cms.utils.i18n import get_languages
        from django.contrib.sites.models import Site

        options = conf.load()
        if request.method == "POST":
            try:
                if not options.api_key:
                    raise SupertextError(_("No Supertext API key is configured. Set SUPERTEXT_API_KEY."))
                options.client().validate_api_key()
                messages.success(request, _("Connected. The API key works."))
            except SupertextError as error:
                messages.error(request, localized(error))

        sites = []
        for site in Site.objects.order_by("pk"):
            sites.append({
                "site": site,
                "languages": [
                    {"code": lang["code"], "name": lang.get("name", lang["code"]), "target": options.target_code(lang["code"]),
                     "politeness": options.politeness(lang["code"])}
                    for lang in get_languages(site.pk)
                ],
            })
        context = {
            **self.admin_site.each_context(request),
            "title": _("Supertext settings"),
            "options": options,
            "sites": sites,
            "signup_url": conf.SIGNUP_URL,
            "api_key_url": conf.API_KEY_URL,
            "opts": self.model._meta,
            "version": plugin_version(),
        }
        return TemplateResponse(request, "djangocms_supertext/settings.html", context)


def _edit_url(page, language: str) -> str:
    content = translator.page_content(page, language)
    if content is None:
        return ""
    try:
        from cms.toolbar.utils import get_object_edit_url

        return get_object_edit_url(content, language)
    except Exception:  # noqa: BLE001 - older django CMS
        return content.get_absolute_url(language)


def translate_url(page, language: str) -> str:
    return reverse("admin:djangocms_supertext_translate", args=[page.pk]) + f"?language={language}"
