"""The one exception the SDK raises, and its error codes."""

from __future__ import annotations

import contextlib
import json
import re
from typing import Final

SIGNUP_URL: Final = "https://www.supertext.com/person/en/account/signin"
"""Where administrators create a Supertext account (or log in)."""

API_KEY_URL: Final = "https://www.supertext.com/en/integrations/api"
"""Where they generate the API key (supertext.com → Integrations → API; requires the Admin role)."""

_KEY_HELP = (
    f"No Supertext account yet? Create one at {SIGNUP_URL}. Generate your API key at {API_KEY_URL} "
    "(supertext.com → Integrations → API; requires the Admin role)."
)


class ErrorCode:
    """The values of :attr:`SupertextError.code`. The strings are fixed and shared by all Supertext SDKs."""

    MISSING_API_KEY: Final = "missing_api_key"
    AUTHENTICATION_FAILURE: Final = "authentication_failure"
    INVALID_LANGUAGE_PAIR: Final = "invalid_language_pair"
    UNSUPPORTED_LANGUAGE: Final = "unsupported_language"
    UNSUPPORTED_FEATURE: Final = "unsupported_feature"
    NOT_FOUND: Final = "not_found"
    PAYLOAD_TOO_LARGE: Final = "payload_too_large"
    TOO_MANY_REQUESTS: Final = "too_many_requests"
    SERVICE_UNAVAILABLE: Final = "service_unavailable"
    UNEXPECTED_STATUS: Final = "unexpected_status"
    TRANSPORT_ERROR: Final = "transport_error"
    NO_FILE_ID: Final = "no_file_id"
    TRANSLATION_ERROR: Final = "translation_error"
    QUOTA_EXCEEDED: Final = "quota_exceeded"
    FILE_DELETED: Final = "file_deleted"
    TIMEOUT: Final = "timeout"
    INCOMPLETE_RESPONSE: Final = "incomplete_response"


_MESSAGES: Final = {
    ErrorCode.MISSING_API_KEY: "No Supertext API key is configured. " + _KEY_HELP,
    ErrorCode.AUTHENTICATION_FAILURE: "Supertext rejected the API key. Please check it. " + _KEY_HELP,
    ErrorCode.INVALID_LANGUAGE_PAIR: "Supertext does not support this language pair.",
    ErrorCode.UNSUPPORTED_LANGUAGE: "This language has no Supertext language code. Map it to a Supertext language.",
    ErrorCode.UNSUPPORTED_FEATURE: "Supertext does not support this option for the language pair.",
    ErrorCode.NOT_FOUND: "The file was not found at Supertext (it may have expired or been deleted).",
    ErrorCode.PAYLOAD_TOO_LARGE: "The content is too large for Supertext to translate in one go.",
    ErrorCode.TOO_MANY_REQUESTS: "Too many requests to Supertext. Please try again shortly.",
    ErrorCode.SERVICE_UNAVAILABLE: "The Supertext service is currently unavailable.",
    ErrorCode.UNEXPECTED_STATUS: "Supertext answered with an unexpected HTTP status.",
    ErrorCode.TRANSPORT_ERROR: "Could not reach Supertext.",
    ErrorCode.NO_FILE_ID: "Supertext did not return a file id.",
    ErrorCode.TRANSLATION_ERROR: "Supertext could not translate the document.",
    ErrorCode.QUOTA_EXCEEDED: "Your Supertext translation limit is used up.",
    ErrorCode.FILE_DELETED: "The document was deleted at Supertext before it could be downloaded.",
    ErrorCode.TIMEOUT: "Timed out waiting for the Supertext translation.",
    ErrorCode.INCOMPLETE_RESPONSE: "The translation from Supertext was incomplete.",
}


class SupertextError(Exception):
    """Any failure talking to Supertext.

    ``code`` is one of :class:`ErrorCode`; decide what to show users from it. ``message``
    (also ``str(error)``) is English. ``detail`` is the API's own text (or the network error)
    and is never translated. ``source_lang``/``target_lang`` are set for ``invalid_language_pair``
    and ``unsupported_feature`` when the API names them, and for ``unsupported_language`` (the code
    that has no Supertext language); ``feature`` for ``unsupported_feature`` (e.g. ``politeness``).
    The API key never appears in any of these.
    """

    def __init__(
        self,
        code: str,
        *,
        status: int | None = None,
        detail: str | None = None,
        api_error_code: str | None = None,
        source_lang: str | None = None,
        target_lang: str | None = None,
        feature: str | None = None,
        message: str | None = None,
    ) -> None:
        self.code = code
        self.message = message or _MESSAGES.get(code, "Supertext request failed.")
        self.status = status
        self.detail = detail
        self.api_error_code = api_error_code
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.feature = feature
        super().__init__(self.message)

    def __str__(self) -> str:
        text = self.message
        if self.status is not None:
            text += f" (HTTP {self.status})"
        if self.detail:
            text += f" {self.detail}"
        return text

    def __repr__(self) -> str:
        return f"SupertextError(code={self.code!r}, status={self.status!r}, detail={self.detail!r})"


def _detail(body: str) -> str | None:
    # Error pages are often HTML; keep only their text, short enough for a log line.
    text = re.sub(r"<[^>]*>", "", body).strip(" \t\n\r\f\v")[:200]
    return text or None


def error_for_response(status: int, body: str) -> SupertextError:
    """Maps a non-2xx answer to a :class:`SupertextError` (spec/errors.json)."""
    data: object = None
    with contextlib.suppress(ValueError):
        data = json.loads(body) if body.strip() else None
    fields = data if isinstance(data, dict) else {}

    def text(name: str) -> str | None:
        value = fields.get(name)
        return value if isinstance(value, str) and value else None

    api_error_code = text("error_code")
    source_lang = target_lang = feature = None
    if status in (400, 404) and "INVALID_LANGUAGE_PAIR" in body:
        code = ErrorCode.INVALID_LANGUAGE_PAIR
        source_lang, target_lang = text("source_lang"), text("target_lang")
    elif status == 400 and api_error_code == "FEATURE_ERROR":
        # The pair exists, but not with this option (e.g. politeness for en-US).
        code = ErrorCode.UNSUPPORTED_FEATURE
        source_lang, target_lang, feature = text("source_lang"), text("target_lang"), text("feature")
    elif status in (401, 403):
        code = ErrorCode.AUTHENTICATION_FAILURE
    elif status == 404:
        code = ErrorCode.NOT_FOUND
    elif status == 413:
        code = ErrorCode.PAYLOAD_TOO_LARGE
    elif status == 429:
        code = ErrorCode.TOO_MANY_REQUESTS
    elif 500 <= status <= 599:
        code = ErrorCode.SERVICE_UNAVAILABLE
    else:
        code = ErrorCode.UNEXPECTED_STATUS
    return SupertextError(
        code,
        status=status,
        detail=_detail(body),
        api_error_code=api_error_code,
        source_lang=source_lang,
        target_lang=target_lang,
        feature=feature,
    )
