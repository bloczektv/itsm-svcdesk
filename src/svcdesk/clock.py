# ai-generated: 90% - Claude Code drafted, reviewed by the author

"""Per-request test clock (docs/API.md section 8, R-21)."""

import os
from datetime import datetime, timezone

from fastapi import Request

from .exceptions import ValidationFailed
from .timeutil import parse_instant


def _test_clock_enabled() -> bool:
    return os.environ.get("SVCDESK_TEST_CLOCK", "0").strip().lower() in ("1", "true")


def resolve_now(request: Request) -> datetime:
    """Return 'now' for this request: the X-Test-Clock header when enabled and present, else real UTC time."""
    if _test_clock_enabled():
        header = request.headers.get("X-Test-Clock")
        if header:
            try:
                return parse_instant(header)
            except ValueError:
                raise ValidationFailed("X-Test-Clock is not a valid RFC 3339 instant")
    return datetime.now(timezone.utc)
