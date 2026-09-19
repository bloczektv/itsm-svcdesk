# ai-generated: 90% - Claude Code drafted, reviewed by the author

"""RFC 3339 instant parsing and formatting shared by clock.py, sla.py and state_machine.py."""

from datetime import datetime, timezone


def parse_instant(value: str) -> datetime:
    """Parse an RFC 3339 instant. Raises ValueError on anything malformed or without an offset."""
    v = value.strip()
    if v.endswith("Z") or v.endswith("z"):
        v = v[:-1] + "+00:00"
    dt = datetime.fromisoformat(v)
    if dt.tzinfo is None:
        raise ValueError(f"instant without a UTC offset: {value!r}")
    return dt.astimezone(timezone.utc)


def fmt_instant(dt: datetime) -> str:
    """Format as a whole-second UTC instant with a Z suffix, e.g. 2026-10-14T10:00:00Z."""
    dt = dt.astimezone(timezone.utc).replace(microsecond=0)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
