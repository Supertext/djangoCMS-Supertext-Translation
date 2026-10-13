"""Supertext AI file translation API v1. A later API version gets its own subpackage
(``supertext.v2``) next to this one, so integrations can move at their own pace.

    from supertext import v1

    client = v1.SupertextClient(api_key)
    target = v1.Languages.target(cms_locale, {"de": "de-CH"})
    texts = client.translate_texts({"title": "Hello", "body": v1.Segment("<p>Hi</p>", html=True)}, target)

No Supertext account yet? Create one at https://www.supertext.com/person/en/account/signin.
Generate your API key at https://www.supertext.com/en/integrations/api
(supertext.com → Integrations → API; requires the Admin role).
"""

from ..transport import HttpRequest, HttpResponse, Transport, UrllibTransport
from . import languages
from .api_key_check import KEY_CHECK_TIMEOUT, ApiKeyCheck, ApiKeyCheckStatus, api_key_fingerprint
from .client import (
    DEFAULT_MAX_CHARACTERS,
    LIVE_BASE_URL,
    FeatureSupport,
    Politeness,
    SupertextClient,
    auth_header,
    plan_batches,
    retry_delay_ms,
)
from .errors import API_KEY_URL, SIGNUP_URL, ErrorCode, SupertextError
from .html_document import HtmlDocument, Segment
from .languages import LanguageMapping, Languages, SourceLanguage, TargetLanguage
from .reporting import (
    DEFAULT_REPORT_URL,
    FAILURE_BACKOFF,
    REPORT_TIMEOUT,
    InstallationReporter,
    NameVersion,
    PingResponse,
    ReporterResult,
    ReporterState,
    ReportEvent,
    StateInput,
    ping_response,
    reporter_state,
    reports_enabled,
)

__all__ = [
    "API_KEY_URL",
    "DEFAULT_MAX_CHARACTERS",
    "DEFAULT_REPORT_URL",
    "FAILURE_BACKOFF",
    "KEY_CHECK_TIMEOUT",
    "LIVE_BASE_URL",
    "REPORT_TIMEOUT",
    "SIGNUP_URL",
    "ApiKeyCheck",
    "ApiKeyCheckStatus",
    "ErrorCode",
    "FeatureSupport",
    "HtmlDocument",
    "HttpRequest",
    "HttpResponse",
    "InstallationReporter",
    "LanguageMapping",
    "Languages",
    "NameVersion",
    "PingResponse",
    "Politeness",
    "ReportEvent",
    "ReporterResult",
    "ReporterState",
    "Segment",
    "SourceLanguage",
    "StateInput",
    "SupertextClient",
    "SupertextError",
    "TargetLanguage",
    "Transport",
    "UrllibTransport",
    "api_key_fingerprint",
    "auth_header",
    "languages",
    "ping_response",
    "plan_batches",
    "reporter_state",
    "reports_enabled",
    "retry_delay_ms",
]
