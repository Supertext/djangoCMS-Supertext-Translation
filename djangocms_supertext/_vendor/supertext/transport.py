"""HTTP transport: the one place that does I/O, so tests and integrations can replace it."""

from __future__ import annotations

import http.client
import urllib.error
import urllib.request
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class HttpRequest:
    method: str
    url: str
    headers: Mapping[str, str]
    body: bytes | None = None
    timeout: float = 30.0


@dataclass(frozen=True)
class HttpResponse:
    status: int
    body: bytes = b""
    headers: Mapping[str, str] = field(default_factory=dict)
    """Header names in lower case."""

    def header(self, name: str) -> str | None:
        return self.headers.get(name.lower())

    @property
    def text(self) -> str:
        return self.body.decode("utf-8", errors="replace")


class Transport(Protocol):
    """Sends one request and returns the answer, whatever its status.

    Raise :class:`OSError` (e.g. ``urllib.error.URLError``, ``TimeoutError``) when there is no HTTP
    answer at all; the client turns it into ``SupertextError(transport_error)``.
    """

    def __call__(self, request: HttpRequest) -> HttpResponse: ...


def _lower(headers: Mapping[str, str]) -> dict[str, str]:
    return {name.lower(): value for name, value in headers.items()}


class UrllibTransport:
    """Default transport on :mod:`urllib.request` (honours the usual proxy environment variables)."""

    def __call__(self, request: HttpRequest) -> HttpResponse:
        req = urllib.request.Request(
            request.url, data=request.body, headers=dict(request.headers), method=request.method
        )
        try:
            with urllib.request.urlopen(req, timeout=request.timeout) as response:
                return HttpResponse(response.status, response.read(), _lower(dict(response.headers.items())))
        except urllib.error.HTTPError as error:
            # Non-2xx answers are answers, not transport failures: hand them to the client's mapping.
            with error:
                body = error.read()
            return HttpResponse(error.code, body, _lower(dict(error.headers.items())) if error.headers else {})
        except http.client.HTTPException as error:
            # Malformed answers (e.g. connection closed mid-response) aren't OSErrors; make them one.
            raise OSError(f"{type(error).__name__}: {error}") from error
