"""The API key check result and how the reporter gets it (the check itself is the Supertext SDK's)."""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol

__all__ = ["CallableKeyChecker", "KeyCheck", "KeyChecker", "iso_seconds", "parse_iso"]

_MISSING = object()


@dataclass(frozen=True)
class KeyCheck:
    """The result of the SDK's API key check, as the reporter stores and reports it.

    ``to_dict()`` uses the shared camelCase keys (``checkedAt``, ``httpStatus``, ``errorCode``), so the
    stored form is the same in every language and in the Supertext SDK 0.1 to 0.2 reporter.
    """

    status: str
    """``ok``, ``invalid``, ``missing``, ``unreachable`` or ``error`` (the SDK's statuses)."""
    checked_at: str
    """When the check ran: UTC ISO 8601 without fractions (``2026-10-13T08:00:00Z``)."""
    http_status: int | None = None
    """The HTTP status Supertext answered with; ``None`` without an answer."""
    error_code: str | None = None
    """Supertext's ``error_code``; ``None`` if none."""
    fingerprint: str = ""
    """SHA-256 of the key, to notice a changed key. Kept locally, never sent. '' for a blank key."""

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "checkedAt": self.checked_at,
            "httpStatus": self.http_status,
            "errorCode": self.error_code,
            "fingerprint": self.fingerprint,
        }

    @classmethod
    def from_value(cls, value: object) -> KeyCheck | None:
        """A key check from a :class:`KeyCheck`, any object with its attributes (the SDK's ``ApiKeyCheck``)
        or a mapping with snake_case or camelCase keys; ``None`` without a ``status`` and ``checked_at`` string.
        """
        if isinstance(value, KeyCheck):
            return value
        if value is None:
            return None

        def get(snake: str, camel: str) -> object:
            if isinstance(value, Mapping):
                return value.get(snake, value.get(camel))
            found = getattr(value, snake, _MISSING)
            return getattr(value, camel, None) if found is _MISSING else found

        try:
            status, checked_at = get("status", "status"), get("checked_at", "checkedAt")
            http_status, error_code = get("http_status", "httpStatus"), get("error_code", "errorCode")
            fingerprint = get("fingerprint", "fingerprint")
        except Exception:  # a hostile object's attribute access
            return None
        if not isinstance(status, str) or not isinstance(checked_at, str):
            return None
        return cls(
            status=status,
            checked_at=checked_at,
            http_status=http_status if isinstance(http_status, int) and not isinstance(http_status, bool) else None,
            error_code=error_code if isinstance(error_code, str) else None,
            fingerprint=fingerprint if isinstance(fingerprint, str) else "",
        )


class KeyChecker(Protocol):
    """How the reporter checks the API key. Plugins pass the bundled Supertext SDK's functions, e.g.
    ``CallableKeyChecker(check=lambda k: SupertextClient(k).check_api_key(), fingerprint=api_key_fingerprint)``.

    ``check`` returns a :class:`KeyCheck`, the SDK's ``ApiKeyCheck`` or a mapping (see :meth:`KeyCheck.from_value`).
    """

    def check(self, api_key: str) -> object: ...

    def fingerprint(self, api_key: str) -> str: ...


@dataclass(frozen=True)
class CallableKeyChecker:
    """A :class:`KeyChecker` from two functions."""

    check_function: Callable[[str], object]
    fingerprint_function: Callable[[str], str]

    def __init__(self, check: Callable[[str], object], fingerprint: Callable[[str], str]) -> None:
        object.__setattr__(self, "check_function", check)
        object.__setattr__(self, "fingerprint_function", fingerprint)

    def check(self, api_key: str) -> object:
        return self.check_function(api_key)

    def fingerprint(self, api_key: str) -> str:
        return self.fingerprint_function(api_key)


def iso_seconds(seconds: float) -> str:
    """``2026-10-13T08:00:00Z`` for a Unix time in seconds (fractions dropped)."""
    return datetime.fromtimestamp(math.floor(seconds), tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(value: str) -> float | None:
    """Unix seconds of an ISO 8601 time (``Z`` or an offset; none = UTC); ``None`` if it isn't one."""
    text = value.strip()
    if text.endswith(("Z", "z")):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.timestamp()
