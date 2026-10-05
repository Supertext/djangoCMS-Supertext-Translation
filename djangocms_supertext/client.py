"""
Supertext AI file translation API v1 (https://api.supertext.com/v1/).

Same protocol as the other Supertext CMS plugins (WordPress, Drupal, TYPO3, Wagtail, …):
submit one HTML document, poll its status, download the translation, delete the file.
No Django imports, so it can be tested on its own.
"""

from __future__ import annotations

import random
import re
import time
from collections.abc import Callable

import requests

LIVE = "https://api.supertext.com/v1/"
STAGING = "https://api.staging.supertext.com/v1/"
TESTING = "https://api.testing.supertext.com/v1/"

#: Stay well below the API's 1,000,000 character limit per document.
MAX_DOCUMENT_CHARACTERS = 900_000

#: Retries after HTTP 429: the API limits requests per second per key.
RATE_LIMIT_RETRIES = 4


class SupertextError(Exception):
    """Any failure talking to Supertext. The message is safe to show to editors."""

    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


def normalize_key(key: str | None) -> str:
    """Supertext shows the key as "Supertext-Auth-Key <key>"; accept it with or without that prefix."""
    return re.sub(r"^Supertext-Auth-Key\s+", "", (key or "").strip(), flags=re.IGNORECASE)


def base_url_for(environment: str = "live", endpoint: str = "") -> str:
    if endpoint and endpoint.strip():
        return endpoint.strip()
    return {"staging": STAGING, "testing": TESTING}.get(environment, LIVE)


def retry_delay(attempt: int, retry_after: str | None = None) -> float:
    """Seconds to wait before retry ``attempt`` (0-based): Retry-After if sent, else 1, 2, 4, 8 plus jitter."""
    if retry_after:
        try:
            seconds = float(retry_after)
            if seconds >= 0:
                return min(30.0, seconds)
        except ValueError:
            pass
    return 2**attempt + random.random() / 4


class SupertextClient:
    def __init__(
        self,
        api_key: str,
        base_url: str = LIVE,
        *,
        poll_timeout: float = 180,
        poll_interval: float = 2,
        request_timeout: float = 30,
        session: requests.Session | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.api_key = normalize_key(api_key)
        self.base_url = (base_url or LIVE).rstrip("/") + "/"
        self.poll_timeout = poll_timeout
        self.poll_interval = poll_interval
        self.request_timeout = request_timeout
        self.session = session or requests.Session()
        self.sleep = sleep

    @property
    def has_api_key(self) -> bool:
        return bool(self.api_key)

    def translate_document(self, html: str, target_language: str, source_language: str = "", politeness: str = "default") -> str:
        """Translates a complete HTML document and returns the translated HTML.

        ``target_language`` is a BCP-47 code such as ``de-CH``; of ``source_language`` only the
        primary subtag is sent (empty: auto-detect); ``politeness`` is default, more or less.
        """
        file_id = self._submit(html, target_language, source_language, politeness)
        try:
            self._wait_until_done(file_id)
            return self._download(file_id)
        finally:
            try:
                self._request("DELETE", f"translate/ai/file/{file_id}")
            except SupertextError:
                pass  # files expire after 24 hours anyway

    def validate_api_key(self) -> None:
        """Cost-free check that the key is accepted."""
        self._request("GET", "features")

    # -------------------------------------------------------------------------------

    def _submit(self, html: str, target_language: str, source_language: str, politeness: str) -> str:
        data = {"target_lang": target_language}
        source = re.split(r"[-_]", source_language or "")[0].lower()
        if source:
            # A full tag such as "en-GB" as source is rejected with INVALID_LANGUAGE_PAIR.
            data["source_lang"] = source
        if politeness in ("more", "less"):
            data["politeness"] = politeness
        # The part's Content-Type must be exactly "text/html" (no charset), or the API answers 415.
        files = {"file": ("content.html", html.encode("utf-8"), "text/html")}
        file_id = str(self._request("POST", "translate/ai/file", data=data, files=files).json().get("file_id") or "")
        if not file_id:
            raise SupertextError("Supertext did not return a file id.")
        return file_id

    def _wait_until_done(self, file_id: str) -> None:
        deadline = time.monotonic() + self.poll_timeout
        while True:
            status = str(self._request("GET", f"translate/ai/file/{file_id}/status").json().get("status") or "")
            if status == "done":
                return
            if status == "error":
                raise SupertextError("Supertext could not translate the document.")
            if status == "limit_exceeded":
                raise SupertextError("Your Supertext translation limit is exceeded. Please upgrade your subscription.")
            if status == "deleted":
                raise SupertextError("The document was deleted at Supertext before it could be downloaded.")
            if time.monotonic() >= deadline:
                raise SupertextError("Timed out waiting for the Supertext translation.")
            self.sleep(self.poll_interval)

    def _download(self, file_id: str) -> str:
        response = self._request("GET", f"translate/ai/file/{file_id}/translation")
        response.encoding = "utf-8"
        body = response.text
        if not body.strip():
            raise SupertextError("The translated document was empty.")
        return body

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        if not self.api_key:
            raise SupertextError("No Supertext API key is configured.")
        headers = {"Accept": "application/json", "Authorization": f"Supertext-Auth-Key {self.api_key}"}
        for attempt in range(RATE_LIMIT_RETRIES + 1):
            try:
                response = self.session.request(method, self.base_url + path, headers=headers, timeout=self.request_timeout, **kwargs)
            except requests.RequestException as error:
                raise SupertextError(f"Could not reach Supertext: {error}") from error
            if response.status_code != 429 or attempt >= RATE_LIMIT_RETRIES:
                break
            self.sleep(retry_delay(attempt, response.headers.get("Retry-After")))

        code = response.status_code
        if 200 <= code < 300:
            return response
        if code in (401, 403):
            message = "Authentication failed. Please check the Supertext API key."
        elif code == 404:
            message = "The requested Supertext resource was not found."
        elif code == 413:
            message = "The content is too large for Supertext to translate in one go."
        elif code == 429:
            message = "Too many requests to Supertext. Please try again shortly."
        elif code >= 500:
            message = "The Supertext service is currently unavailable."
        else:
            message = f"Supertext answered with HTTP {code}."
        detail = re.sub(r"<[^>]*>", "", response.text or "").strip()
        if detail:
            message += f" ({detail[:200]})"
        raise SupertextError(message, code)
