"""Languages of the Supertext AI file translation API v1 (spec/languages.json, from the live ``GET features``,
October 2026).

There is no default region and no guessing: an integration maps its CMS languages to these codes. A CMS
code that equals a Supertext code (apart from case and ``_``/``-``) is used as it is; anything else is an
``unsupported_language`` error until the administrator maps it. For the live list, use
:meth:`SupertextClient.get_features() <supertext.v1.SupertextClient.get_features>`.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final

from .errors import ErrorCode, SupertextError

__all__ = [
    "SOURCES",
    "TARGETS",
    "LanguageMapping",
    "Languages",
    "SourceLanguage",
    "TargetLanguage",
    "is_supported_source",
    "is_supported_target",
    "match_source",
    "match_target",
    "source",
    "supports_politeness",
    "target",
]


@dataclass(frozen=True)
class SourceLanguage:
    code: str
    name: str
    """English name."""


@dataclass(frozen=True)
class TargetLanguage:
    code: str
    name: str
    """English name."""
    politeness: bool
    """Whether formal/informal (``politeness`` ``more``/``less``) is offered; else the API answers FEATURE_ERROR."""


SOURCES: Final[tuple[SourceLanguage, ...]] = (
    SourceLanguage("bg", "Bulgarian"),
    SourceLanguage("cs", "Czech"),
    SourceLanguage("da", "Danish"),
    SourceLanguage("de", "German"),
    SourceLanguage("el", "Greek"),
    SourceLanguage("en", "English"),
    SourceLanguage("es", "Spanish"),
    SourceLanguage("fi", "Finnish"),
    SourceLanguage("fr", "French"),
    SourceLanguage("gsw", "Swiss German"),
    SourceLanguage("hr", "Croatian"),
    SourceLanguage("hu", "Hungarian"),
    SourceLanguage("it", "Italian"),
    SourceLanguage("ja", "Japanese"),
    SourceLanguage("ko", "Korean"),
    SourceLanguage("nb", "Norwegian Bokmål"),
    SourceLanguage("nl", "Dutch"),
    SourceLanguage("pl", "Polish"),
    SourceLanguage("pt", "Portuguese"),
    SourceLanguage("rm", "Romansh"),
    SourceLanguage("ru", "Russian"),
    SourceLanguage("sk", "Slovak"),
    SourceLanguage("sl", "Slovenian"),
    SourceLanguage("sq", "Albanian"),
    SourceLanguage("sr", "Serbian"),
    SourceLanguage("sv", "Swedish"),
    SourceLanguage("tr", "Turkish"),
    SourceLanguage("zh", "Chinese"),
)
"""Source languages (bare codes)."""

TARGETS: Final[tuple[TargetLanguage, ...]] = (
    TargetLanguage("bg", "Bulgarian", True),
    TargetLanguage("cs", "Czech", True),
    TargetLanguage("da", "Danish", True),
    TargetLanguage("de-AT", "German (Austria)", True),
    TargetLanguage("de-CH", "German (Switzerland)", True),
    TargetLanguage("de-DE", "German (Germany)", True),
    TargetLanguage("el", "Greek", True),
    TargetLanguage("en-GB", "English (United Kingdom)", False),
    TargetLanguage("en-US", "English (United States)", False),
    TargetLanguage("es", "Spanish", True),
    TargetLanguage("fi", "Finnish", True),
    TargetLanguage("fr-CH", "French (Switzerland)", True),
    TargetLanguage("fr-FR", "French (France)", True),
    TargetLanguage("gsw-u-sd-chbe", "Swiss German (Bern)", False),
    TargetLanguage("gsw-u-sd-chzh", "Swiss German (Zurich)", False),
    TargetLanguage("hr", "Croatian", True),
    TargetLanguage("hu", "Hungarian", True),
    TargetLanguage("it-CH", "Italian (Switzerland)", True),
    TargetLanguage("it-IT", "Italian (Italy)", True),
    TargetLanguage("ja", "Japanese", True),
    TargetLanguage("ko", "Korean", True),
    TargetLanguage("nb", "Norwegian Bokmål", True),
    TargetLanguage("nl", "Dutch", True),
    TargetLanguage("pl", "Polish", True),
    TargetLanguage("pt-BR", "Portuguese (Brazil)", True),
    TargetLanguage("pt-PT", "Portuguese (Portugal)", True),
    TargetLanguage("rm", "Romansh", False),
    TargetLanguage("ru", "Russian", True),
    TargetLanguage("sk", "Slovak", True),
    TargetLanguage("sl", "Slovenian", True),
    TargetLanguage("sq", "Albanian", False),
    TargetLanguage("sr-Cyrl", "Serbian (Cyrillic)", False),
    TargetLanguage("sr-Latn", "Serbian (Latin)", False),
    TargetLanguage("sv", "Swedish", True),
    TargetLanguage("tr", "Turkish", True),
    TargetLanguage("zh-Hans", "Chinese (Simplified)", True),
    TargetLanguage("zh-Hant", "Chinese (Traditional)", True),
)
"""Target languages, exactly as Supertext expects them."""

LanguageMapping = Mapping[str, str]
"""CMS language → Supertext code, e.g. ``{"de": "de-CH", "no": "nb"}`` (the integration's language setting)."""


def _key(code: str) -> str:
    # Case, "_" vs "-" and surrounding spaces don't matter when comparing codes.
    return code.strip().replace("_", "-").lower()


_SOURCES: Final = {_key(language.code): language for language in SOURCES}
_TARGETS: Final = {_key(language.code): language for language in TARGETS}


def match_target(code: str) -> str | None:
    """The supported target that equals ``code`` (apart from case and ``_``/``-``), else ``None``.

    ``de`` → ``None``, ``de_ch`` → ``de-CH``.
    """
    language = _TARGETS.get(_key(code))
    return language.code if language else None


def match_source(code: str) -> str | None:
    """The supported source for ``code``: exact match, else its first subtag (``en-US`` → ``en``), else ``None``."""
    key = _key(code)
    if not key:
        return None
    language = _SOURCES.get(key) or _SOURCES.get(key.split("-")[0])
    return language.code if language else None


def _mapped(code: str, mapping: LanguageMapping | None) -> str | None:
    if not mapping:
        return None
    wanted = _key(code)
    for cms_code, supertext_code in mapping.items():
        if _key(cms_code) == wanted and isinstance(supertext_code, str) and supertext_code.strip():
            return supertext_code.strip()
    return None


def target(code: str, mapping: LanguageMapping | None = None) -> str:
    """The target code to send for a CMS language.

    The mapping's value (sent as it is, even if it isn't in :data:`TARGETS`), else an exact match,
    else ``SupertextError(unsupported_language)`` with ``target_lang`` set (nothing is sent).
    """
    result = _mapped(code, mapping) or match_target(code)
    if result is None:
        raise SupertextError(ErrorCode.UNSUPPORTED_LANGUAGE, target_lang=code.strip() or None)
    return result


def source(code: str, mapping: LanguageMapping | None = None) -> str:
    """The source code to send: the mapping's value, else :func:`match_source`, else ``unsupported_language``.

    ``""`` stays ``""`` (auto-detect).
    """
    if not code.strip():
        return ""
    result = _mapped(code, mapping) or match_source(code)
    if result is None:
        raise SupertextError(ErrorCode.UNSUPPORTED_LANGUAGE, source_lang=code.strip())
    return result


def supports_politeness(target_code: str) -> bool | None:
    """Whether a supported target offers formal/informal; ``None`` for a code that isn't in :data:`TARGETS`."""
    language = _TARGETS.get(_key(target_code))
    return language.politeness if language else None


def is_supported_target(code: str) -> bool:
    return match_target(code) is not None


def is_supported_source(code: str) -> bool:
    return _key(code) in _SOURCES


class Languages:
    """The language helpers in one place, like the other Supertext SDKs: ``Languages.target("de", {"de": "de-CH"})``."""

    SOURCES: Final = SOURCES
    TARGETS: Final = TARGETS
    match_target = staticmethod(match_target)
    match_source = staticmethod(match_source)
    target = staticmethod(target)
    source = staticmethod(source)
    supports_politeness = staticmethod(supports_politeness)
    is_supported_target = staticmethod(is_supported_target)
    is_supported_source = staticmethod(is_supported_source)
