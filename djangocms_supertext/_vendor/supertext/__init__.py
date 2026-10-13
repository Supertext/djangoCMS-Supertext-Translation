"""Supertext AI translation API client: translate HTML and texts, with language codes,
rate-limit retries and HTML packing handled for you.

    import supertext

    client = supertext.Client(api_key)
    texts = client.translate_texts({"title": "Hello", "body": supertext.Segment("<p>Hi</p>", html=True)}, "de-CH")
"""

from importlib.metadata import PackageNotFoundError, version

from . import language_codes
from .client import (
    DEFAULT_MAX_CHARACTERS,
    LIVE_BASE_URL,
    Client,
    Politeness,
    auth_header,
    plan_batches,
    retry_delay_ms,
)
from .errors import API_KEY_URL, SIGNUP_URL, ErrorCode, SupertextError
from .html_document import HtmlDocument, Segment
from .transport import HttpRequest, HttpResponse, Transport, UrllibTransport

LanguageCodes = language_codes
"""Alias matching the other Supertext SDKs: ``LanguageCodes.target("de")``."""

try:
    __version__ = version("supertext-sdk")
except PackageNotFoundError:  # running from a source checkout without installing
    __version__ = "0.0.0"

__all__ = [
    "API_KEY_URL",
    "DEFAULT_MAX_CHARACTERS",
    "LIVE_BASE_URL",
    "SIGNUP_URL",
    "Client",
    "ErrorCode",
    "HtmlDocument",
    "HttpRequest",
    "HttpResponse",
    "LanguageCodes",
    "Politeness",
    "Segment",
    "SupertextError",
    "Transport",
    "UrllibTransport",
    "__version__",
    "auth_header",
    "language_codes",
    "plan_batches",
    "retry_delay_ms",
]
