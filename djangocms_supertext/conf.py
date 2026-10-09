"""
Settings: the ``SUPERTEXT`` dict in Django settings, plus environment variables.

    SUPERTEXT = {
        "API_KEY": "...",                 # or the SUPERTEXT_API_KEY environment variable (wins)
        "ENVIRONMENT": "live",            # live | staging | testing
        "API_URL": "",                    # custom base URL; or SUPERTEXT_API_URL (wins)
        "LANGUAGES": {"de": {"code": "de-CH", "politeness": "more"}},
        "TIMEOUT": 180,                   # seconds per language
        "PLUGIN_FIELDS": {"MyPlugin": {"heading": "text", "content": "html"}},
    }
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from .client import API_KEY_URL, SIGNUP_URL, SupertextClient, base_url_for, normalize_key  # noqa: F401 (URLs re-exported)


#: Plugin fields translated out of the box: plugin type -> {model field: "text" | "html"}.
DEFAULT_PLUGIN_FIELDS: dict[str, dict[str, str]] = {
    "TextPlugin": {"body": "html"},  # djangocms-text (and djangocms-text-ckeditor)
    "LinkPlugin": {"name": "text"},  # djangocms-link
    "PicturePlugin": {"caption_text": "text"},  # djangocms-picture
    "FilePlugin": {"file_name": "text"},  # djangocms-file
    "VideoPlayerPlugin": {"label": "text"},  # djangocms-video
}


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

    @property
    def base_url(self) -> str:
        return base_url_for(self.environment, self.api_url)

    def target_code(self, language_code: str) -> str:
        """Supertext code for a django CMS language: the LANGUAGES override, else BCP-47 (de-ch -> de-CH)."""
        override = (self.language(language_code).get("code") or "").strip()
        return override or bcp47(language_code)

    def politeness(self, language_code: str) -> str:
        value = self.language(language_code).get("politeness") or "default"
        return value if value in ("more", "less") else "default"

    def language(self, language_code: str) -> dict[str, str]:
        for key in (language_code, language_code.lower(), bcp47(language_code)):
            if key in self.languages:
                return self.languages[key] or {}
        return {}

    def client(self, **kwargs) -> SupertextClient:
        return SupertextClient(self.api_key, self.base_url, poll_timeout=self.timeout, poll_interval=self.poll_interval, **kwargs)


def bcp47(language_code: str) -> str:
    """de-ch -> de-CH, zh-hans -> zh-Hans, fr -> fr."""
    parts = language_code.replace("_", "-").split("-")
    out = [parts[0].lower()]
    for part in parts[1:]:
        out.append(part.upper() if len(part) == 2 else part.capitalize())
    return "-".join(out)


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
    )
