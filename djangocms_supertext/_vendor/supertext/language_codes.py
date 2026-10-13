"""Language codes as the Supertext AI file API wants them (spec/language-codes.json).

Source = bare language (``en``), target = regional code (``de-DE``). The API rejects bare
targets and regional sources with ``INVALID_LANGUAGE_PAIR``, the most common integration bug.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Final

DEFAULT_REGIONS: Final[Mapping[str, str]] = {
    "ar": "ar-SA", "bg": "bg-BG", "cs": "cs-CZ", "da": "da-DK", "de": "de-DE", "el": "el-GR",
    "en": "en-US", "es": "es-ES", "et": "et-EE", "fi": "fi-FI", "fr": "fr-FR", "hr": "hr-HR",
    "hu": "hu-HU", "it": "it-IT", "ja": "ja-JP", "ko": "ko-KR", "lt": "lt-LT", "lv": "lv-LV",
    "nb": "nb-NO", "nl": "nl-NL", "pl": "pl-PL", "pt": "pt-PT", "ro": "ro-RO", "ru": "ru-RU",
    "sk": "sk-SK", "sl": "sl-SI", "sr": "sr-RS", "sv": "sv-SE", "th": "th-TH", "tr": "tr-TR",
    "uk": "uk-UA", "vi": "vi-VN", "zh": "zh-CN",
}  # fmt: skip
"""Region used when a CMS only has a bare language as target."""

_VALID = re.compile(r"[a-z]{2,3}(-[A-Z][a-z]{3})?(-([A-Z]{2}|[0-9]{3}))?")


def normalize(code: str) -> str:
    """``" de_ch "`` → ``de-CH``, ``zh_hant_tw`` → ``zh-Hant-TW``; other subtags (``419``) unchanged."""
    parts = code.strip().replace("_", "-").split("-")
    out = [parts[0].lower()]
    for part in parts[1:]:
        letters = part.isascii() and part.isalpha()
        if len(part) == 2 and letters:
            out.append(part.upper())
        elif len(part) == 4 and letters:
            out.append(part[:1].upper() + part[1:].lower())
        else:
            out.append(part)
    return "-".join(out)


def _override(code: str, overrides: Mapping[str, str] | None) -> str | None:
    if not overrides:
        return None
    wanted = normalize(code)
    for key, value in overrides.items():
        if normalize(key) == wanted and value.strip():
            return value
    return None


def source(code: str, overrides: Mapping[str, str] | None = None) -> str:
    """The bare language to send as ``source_lang`` (``en-US`` → ``en``); ``""`` for ``""`` (auto-detect)."""
    return normalize(_override(code, overrides) or code).split("-")[0]


def target(code: str, overrides: Mapping[str, str] | None = None) -> str:
    """The regional code to send as ``target_lang``: ``de`` → ``de-DE``, ``de_ch`` → ``de-CH``.

    ``overrides`` maps CMS locales to Supertext codes (e.g. ``{"de": "de-CH"}`` for a Swiss site).
    Unknown bare languages are returned unchanged; the API will reject them.
    """
    normalized = normalize(_override(code, overrides) or code)
    if "-" not in normalized:
        return DEFAULT_REGIONS.get(normalized, normalized)
    return normalized


def is_valid(code: str) -> bool:
    """Whether the code (after :func:`normalize`) has the shape ``ll``, ``ll-RR``, ``ll-Scri-RR`` or ``ll-419``."""
    return _VALID.fullmatch(normalize(code)) is not None
