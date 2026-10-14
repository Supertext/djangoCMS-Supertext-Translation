"""
Settings: the ``SUPERTEXT`` dict in Django settings, plus environment variables.

    SUPERTEXT = {
        "API_KEY": "...",                 # or the SUPERTEXT_API_KEY environment variable (wins)
        "ENVIRONMENT": "live",            # live | staging | testing
        "API_URL": "",                    # custom base URL; or SUPERTEXT_API_URL (wins)
        "LANGUAGES": {"de": {"code": "de-CH", "politeness": "more"}},
        "TIMEOUT": 180,                   # seconds per language
        "PLUGIN_FIELDS": {"MyPlugin": {"heading": "text", "content": "html"}},
        "VERSION_REPORTS": True,          # "Send version information to Supertext"; SUPERTEXT_VERSION_REPORTS (wins)
        "SITE_URL": "",                   # the site's base URL for version reports (default: the request's)
    }

Language codes follow the Supertext SDK (``Languages``), without guessing: the ``code`` under
``LANGUAGES`` wins; otherwise a django CMS code that is a Supertext code apart from case and
``_``/``-`` (``de-ch`` → ``de-CH``, ``es``) is used; anything else is ``unsupported_language``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from ._vendor.supertext import v1 as sdk
from .client import API_KEY_URL, SIGNUP_URL, Languages, SupertextClient, SupertextError, base_url_for, normalize_key  # noqa: F401 (URLs re-exported)


#: Plugin fields translated out of the box: plugin type -> {model field: "text" | "html"}.
DEFAULT_PLUGIN_FIELDS: dict[str, dict[str, str]] = {
    "TextPlugin": {"body": "html"},  # djangocms-text (and djangocms-text-ckeditor)
    "LinkPlugin": {"name": "text"},  # djangocms-link
    "PicturePlugin": {"caption_text": "text"},  # djangocms-picture
    "FilePlugin": {"file_name": "text"},  # djangocms-file
    "VideoPlayerPlugin": {"label": "text"},  # djangocms-video
}


def _key(language_code: str) -> str:
    """Language codes compare like the SDK's: case, ``_``/``-`` and spaces don't matter."""
    return language_code.strip().replace("_", "-").lower()


@dataclass
class Options:
    api_key: str = ""
    api_key_source: str = ""  # "environment", "settings" or ""
    environment: str = "live"
    api_url: str = ""
    languages: dict[str, dict[str, str]] = field(default_factory=dict)
    timeout: float = 180
    poll_interval: float = 2
    plugin_fields: dict[str, dict[str, str]] = field(default_factory=dict)
    version_reports: bool | None = None  # the VERSION_REPORTS setting (None: not set, default on)
    site_url: str = ""

    @property
    def base_url(self) -> str:
        return base_url_for(self.environment, self.api_url)

    @property
    def reports_enabled(self) -> bool:
        """*Send version information to Supertext*: SUPERTEXT_VERSION_REPORTS wins over VERSION_REPORTS (default on)."""
        return sdk.reports_enabled(self.version_reports)

    @property
    def reports_from_environment(self) -> bool:
        return (os.environ.get("SUPERTEXT_VERSION_REPORTS") or "").strip().lower() in ("0", "false", "off", "no", "1", "true", "on", "yes")

    def mapping(self) -> dict[str, str]:
        """django CMS language → Supertext code, from ``LANGUAGES`` → ``code``."""
        return {cms_code: str(entry.get("code") or "").strip() for cms_code, entry in self.languages.items() if (entry or {}).get("code")}

    def target_code(self, language_code: str) -> str:
        """Supertext target for a django CMS language: the ``LANGUAGES`` mapping, else an exact Supertext code
        (``de-ch`` → ``de-CH``), else :class:`SupertextError` ``unsupported_language`` (nothing is sent)."""
        try:
            return Languages.target(language_code, self.mapping())
        except sdk.SupertextError as error:
            raise SupertextError.from_sdk(error) from error

    def target_code_or_none(self, language_code: str) -> str | None:
        """The target code, or None when the language has no Supertext language yet (settings page)."""
        try:
            return self.target_code(language_code)
        except SupertextError:
            return None

    def source_code(self, language_code: str) -> str:
        """Supertext source for a django CMS language: the ``LANGUAGES`` mapping in its source form (one mapping
        for both directions: ``de-CH`` → ``de``), else the code's language (``en-us`` → ``en``), else
        ``unsupported_language``."""
        try:
            return Languages.source(language_code, self.mapping())
        except sdk.SupertextError as error:
            raise SupertextError.from_sdk(error) from error

    def mapping_for(self, language_code: str) -> str:
        return str(self.language(language_code).get("code") or "").strip()

    def politeness(self, language_code: str) -> str:
        value = self.language(language_code).get("politeness") or "default"
        return value if value in ("more", "less") else "default"

    def language(self, language_code: str) -> dict[str, str]:
        wanted = _key(language_code)
        for key, entry in self.languages.items():
            if _key(key) == wanted:
                return entry or {}
        return {}

    def client(self, **kwargs) -> SupertextClient:
        return SupertextClient(self.api_key, self.base_url, poll_timeout=self.timeout, poll_interval=self.poll_interval, **kwargs)


def _bool_or_none(value) -> bool | None:
    if value is None or value == "":
        return None
    if isinstance(value, str):
        return value.strip().lower() not in ("0", "false", "off", "no")
    return bool(value)


def load(options: dict | None = None) -> Options:
    if options is None:
        from django.conf import settings

        options = getattr(settings, "SUPERTEXT", None) or {}

    env_key = os.environ.get("SUPERTEXT_API_KEY", "")
    key = env_key or str(options.get("API_KEY") or "")
    plugin_fields = {k: dict(v) for k, v in DEFAULT_PLUGIN_FIELDS.items()}
    for plugin_type, fields in (options.get("PLUGIN_FIELDS") or {}).items():
        plugin_fields[str(plugin_type)] = {str(name): str(kind) for name, kind in (fields or {}).items()}
    return Options(
        api_key=normalize_key(key),
        api_key_source="environment" if env_key else ("settings" if key else ""),
        environment=str(options.get("ENVIRONMENT") or "live"),
        api_url=os.environ.get("SUPERTEXT_API_URL", "") or str(options.get("API_URL") or ""),
        languages={str(k): dict(v or {}) for k, v in (options.get("LANGUAGES") or {}).items()},
        timeout=float(options.get("TIMEOUT") or 180),
        poll_interval=float(options.get("POLL_INTERVAL") or 2),
        plugin_fields=plugin_fields,
        version_reports=_bool_or_none(options.get("VERSION_REPORTS")),
        site_url=str(options.get("SITE_URL") or "").strip().rstrip("/"),
    )
