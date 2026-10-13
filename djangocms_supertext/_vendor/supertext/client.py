"""Client for the Supertext AI file translation API v1.

Protocol: POST an HTML file → poll its status → GET the translation → DELETE the file.
"""

from __future__ import annotations

import contextlib
import json
import random
import re
import time
import uuid
from collections.abc import Callable, Mapping
from typing import Final, Literal
from urllib.parse import quote

from . import html_document, language_codes
from .errors import ErrorCode, SupertextError, error_for_response
from .html_document import Segment
from .transport import HttpRequest, HttpResponse, Transport, UrllibTransport

LIVE_BASE_URL: Final = "https://api.supertext.com/v1/"

DEFAULT_MAX_CHARACTERS: Final = 900_000
"""Characters per document in :meth:`Client.translate_texts`: well below the API's limit of 1,000,000."""

Politeness = Literal["default", "more", "less"]
"""``more`` = formal address (Sie, vous), ``less`` = informal (du, tu), ``default`` = let Supertext decide."""

_USER_AGENT: Final = "supertext-sdk-python"
_PREFIX = re.compile(r"^supertext-auth-key(?:\s+|$)", re.IGNORECASE)
_RETRY_AFTER = re.compile(r"[0-9]+(?:\.[0-9]+)?")


def auth_header(api_key: str | None) -> str:
    """The ``Authorization`` value for a key as pasted by an administrator (spec/auth-header.json).

    Supertext shows the key with its ``Supertext-Auth-Key`` prefix, so a pasted prefix is stripped
    and exactly one is sent. A blank key raises ``SupertextError(missing_api_key)``.
    """
    key = _PREFIX.sub("", (api_key or "").strip()).strip()
    if not key:
        raise SupertextError(ErrorCode.MISSING_API_KEY)
    return f"Supertext-Auth-Key {key}"


def retry_delay_ms(attempt: int, retry_after: str | None = None, rand: Callable[[], float] = random.random) -> int:
    """Milliseconds to wait before retrying HTTP 429 number ``attempt`` (0-based; spec/retry-delay.json).

    A ``Retry-After`` in plain seconds wins; otherwise 1, 2, 4, 8, … s plus 0 to 249 ms jitter, so
    that several clients sharing a key don't retry in lockstep. Either way at most 30 s.
    """
    value = (retry_after or "").strip(" \t\n\r\f\v")
    if _RETRY_AFTER.fullmatch(value):
        delay = round(float(value) * 1000)
    else:
        delay = 1000 * (1 << attempt) + min(249, int(rand() * 250))
    return min(30_000, delay)


class Client:
    """Translates HTML documents and texts with Supertext.

    A blank API key doesn't fail here: the first request raises ``SupertextError(missing_api_key)``
    without sending anything, so integrations can build the client before the key is configured.
    Times are in seconds. ``transport``, ``sleep`` and ``clock`` are injectable for tests.
    """

    def __init__(
        self,
        api_key: str | None,
        *,
        base_url: str = LIVE_BASE_URL,
        poll_interval: float = 2.0,
        timeout: float = 180.0,
        request_timeout: float = 30.0,
        max_retries: int = 4,
        user_agent: str | None = None,
        transport: Transport | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._api_key = api_key or ""
        self.base_url = (base_url or LIVE_BASE_URL).rstrip("/") + "/"
        self.poll_interval = poll_interval
        self.timeout = timeout
        self.request_timeout = request_timeout
        self.max_retries = max_retries
        self.user_agent = f"{_USER_AGENT} {user_agent}" if user_agent else _USER_AGENT
        self._transport: Transport = transport or UrllibTransport()
        self._sleep = sleep
        self._clock = clock

    def __repr__(self) -> str:
        # Never show the key.
        return f"Client(base_url={self.base_url!r})"

    # -- Single steps ------------------------------------------------------------------------

    def validate_api_key(self) -> None:
        """Cost-free check that the key is accepted; raises :class:`SupertextError` otherwise."""
        self._request("GET", "features")

    def submit(
        self, html: str, target_lang: str, source_lang: str | None = None, politeness: Politeness = "default"
    ) -> str:
        """Uploads an HTML document and returns its file id.

        Language codes are corrected here (``de`` → ``de-DE`` as target, ``en-US`` → ``en`` as source).
        Without ``source_lang`` Supertext detects the language.
        """
        fields = [("target_lang", language_codes.target(target_lang))]
        source = language_codes.source(source_lang or "")
        if source:
            fields.append(("source_lang", source))
        if politeness in ("more", "less"):
            fields.append(("politeness", politeness))
        body, content_type = _multipart(fields, html)
        response = self._request("POST", "translate/ai/file", body=body, content_type=content_type)
        file_id = _json_field(response, "file_id")
        if not file_id:
            raise SupertextError(ErrorCode.NO_FILE_ID, status=response.status)
        return file_id

    def get_status(self, file_id: str) -> str:
        """The file's status: ``translating``, ``done``, ``error``, ``limit_exceeded``, ``deleted`` (or others)."""
        return _json_field(self._request("GET", f"translate/ai/file/{quote(file_id, safe='')}/status"), "status")

    def wait_until_done(self, file_id: str) -> None:
        """Polls until the file is ``done``; raises on ``error``/``limit_exceeded``/``deleted`` or after ``timeout``."""
        started = self._clock()
        while True:
            status = self.get_status(file_id)
            if status == "done":
                return
            if status == "error":
                raise SupertextError(ErrorCode.TRANSLATION_ERROR)
            if status == "limit_exceeded":
                raise SupertextError(ErrorCode.QUOTA_EXCEEDED)
            if status == "deleted":
                raise SupertextError(ErrorCode.FILE_DELETED)
            # Unknown statuses (e.g. "queued") mean "not yet": keep polling.
            if self._clock() + self.poll_interval - started > self.timeout:
                raise SupertextError(ErrorCode.TIMEOUT)
            self._sleep(self.poll_interval)

    def download(self, file_id: str) -> str:
        """The translated HTML document."""
        text = self._request("GET", f"translate/ai/file/{quote(file_id, safe='')}/translation").text
        if not text.strip():
            raise SupertextError(ErrorCode.INCOMPLETE_RESPONSE)
        return text

    def delete(self, file_id: str) -> None:
        """Deletes the file at Supertext. Never raises: files expire after 24 hours anyway."""
        # Cleanup must never hide the real result (or raise after a success).
        with contextlib.suppress(Exception):
            self._request("DELETE", f"translate/ai/file/{quote(file_id, safe='')}")

    # -- Whole translations ------------------------------------------------------------------

    def translate_html(
        self, html: str, target_lang: str, source_lang: str | None = None, politeness: Politeness = "default"
    ) -> str:
        """Translates a complete HTML document and returns the translated document."""
        file_id = self.submit(html, target_lang, source_lang, politeness)
        try:
            self.wait_until_done(file_id)
            return self.download(file_id)
        finally:
            self.delete(file_id)

    def translate_texts(
        self,
        segments: Mapping[str, Segment | str],
        target_lang: str,
        source_lang: str | None = None,
        politeness: Politeness = "default",
        max_characters: int = DEFAULT_MAX_CHARACTERS,
    ) -> dict[str, str]:
        """Translates texts by key and returns ``{key: translation}`` in input order.

        A value is a :class:`Segment` or a plain ``str`` (shorthand for ``Segment(text)``). Blank
        texts come back unchanged without being sent. Large inputs are split into several
        documents (``max_characters`` each), translated one after the other because the API
        limits requests per second.
        """
        items = {key: value if isinstance(value, Segment) else Segment(value) for key, value in segments.items()}
        result = {key: segment.text for key, segment in items.items()}
        for batch in plan_batches(items, max_characters):
            batch_segments = [items[key] for key in batch]
            translated = self.translate_html(html_document.build(batch_segments), target_lang, source_lang, politeness)
            texts = html_document.parse(translated, batch_segments)
            missing = [key for key, text in zip(batch, texts, strict=True) if text is None]
            if missing:
                raise SupertextError(ErrorCode.INCOMPLETE_RESPONSE, detail="missing: " + ", ".join(missing))
            for key, text in zip(batch, texts, strict=True):
                result[key] = text or ""
        return result

    # -- HTTP --------------------------------------------------------------------------------

    def _request(
        self, method: str, path: str, *, body: bytes | None = None, content_type: str | None = None
    ) -> HttpResponse:
        authorization = auth_header(self._api_key)
        headers = {
            "Authorization": authorization,
            "Accept": "application/json",
            "User-Agent": self.user_agent,
        }
        if content_type:
            headers["Content-Type"] = content_type
        request = HttpRequest(method, self.base_url + path, headers, body, self.request_timeout)
        attempt = 0
        while True:
            try:
                response = self._transport(request)
            except OSError as error:
                detail = _scrub(str(error) or type(error).__name__, authorization)
                raise SupertextError(ErrorCode.TRANSPORT_ERROR, detail=detail) from None
            if response.status != 429 or attempt >= self.max_retries:
                break
            # The API limits requests per second per key; several languages at once hit it.
            self._sleep(retry_delay_ms(attempt, response.header("Retry-After")) / 1000)
            attempt += 1
        if 200 <= response.status < 300:
            return response
        failure = error_for_response(response.status, response.text)
        if failure.detail:
            failure.detail = _scrub(failure.detail, authorization)
        raise failure


def _scrub(text: str, authorization: str) -> str:
    # A misbehaving proxy or server could echo the key back; it must not end up in logs.
    key = authorization.split(" ", 1)[1]
    return text.replace(key, "***")


def plan_batches(segments: Mapping[str, Segment], max_characters: int = DEFAULT_MAX_CHARACTERS) -> list[list[str]]:
    """Splits segments into documents (spec/batching.json): lists of keys, in input order.

    Blank segments are skipped. A segment longer than ``max_characters`` goes alone.
    """
    batches: list[list[str]] = []
    current: list[str] = []
    size = 0
    for key, segment in segments.items():
        if not segment.text.strip(" \t\r\n\f"):
            continue
        length = len(html_document.pack(segment))
        if current and size + length > max_characters:
            batches.append(current)
            current, size = [], 0
        current.append(key)
        size += length
    if current:
        batches.append(current)
    return batches


def _json_field(response: HttpResponse, name: str) -> str:
    try:
        data = json.loads(response.text)
    except ValueError:
        return ""
    value = data.get(name) if isinstance(data, dict) else None
    return str(value) if value is not None else ""


def _multipart(fields: list[tuple[str, str]], html: str) -> tuple[bytes, str]:
    # Built by hand: the file part's Content-Type must be exactly "text/html" (no charset), or the
    # API answers 415. Fields go in the documented order: target_lang, source_lang, politeness, file.
    boundary = "supertext-" + uuid.uuid4().hex
    parts = [
        f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode()
        for name, value in fields
    ]
    parts.append(
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="content.html"\r\n'
        "Content-Type: text/html\r\n\r\n".encode()
        + html.encode("utf-8")
        + f"\r\n--{boundary}--\r\n".encode()
    )
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"
