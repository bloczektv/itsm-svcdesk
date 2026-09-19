# ai-generated: 85% - Claude Code drafted against the API.md section 4 test vectors, reviewed by the author

"""SLA due-instant calculators (docs/API.md section 4) and breach/pause evaluation (section 5).

C1 = wallclock (DECISIONS.md): both P1 targets use the wall-clock clock; P2-P4 always use the
business-hours clock (Mon-Fri, 08:00-16:00 Europe/Warsaw).
"""

from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from .timeutil import parse_instant

WARSAW = ZoneInfo("Europe/Warsaw")
_BUSINESS_START = time(8, 0)
_BUSINESS_END = time(16, 0)

# priority -> (acknowledge-within minutes, resolve-within minutes), docs/API.md section 4
_TARGETS = {
    "P1": (15, 4 * 60),
    "P2": (60, 8 * 60),
    "P3": (4 * 60, 24 * 60),
    "P4": (8 * 60, 72 * 60),
}


def _is_business_day(d) -> bool:
    return d.weekday() < 5  # Monday=0 .. Friday=4


def _next_business_day_open(d) -> datetime:
    nd = d + timedelta(days=1)
    while not _is_business_day(nd):
        nd += timedelta(days=1)
    return datetime.combine(nd, _BUSINESS_START, tzinfo=WARSAW)


def _business_open_at_or_after(local_dt: datetime) -> datetime:
    d = local_dt.date()
    if _is_business_day(d):
        start_today = datetime.combine(d, _BUSINESS_START, tzinfo=WARSAW)
        end_today = datetime.combine(d, _BUSINESS_END, tzinfo=WARSAW)
        if local_dt < start_today:
            return start_today
        if local_dt < end_today:
            return local_dt
    return _next_business_day_open(d)


def wallclock_due(created_at: datetime, minutes: int) -> datetime:
    return created_at + timedelta(minutes=minutes)


def business_hours_due(created_at: datetime, minutes: int) -> datetime:
    """Consume `minutes` of business time starting at or after created_at.

    The tie rule: a target that ends exactly at closing time is due at 16:00 that day, not 08:00
    the next business day (docs/API.md section 4).
    """
    current = _business_open_at_or_after(created_at.astimezone(WARSAW))
    remaining = minutes
    while True:
        window_end = datetime.combine(current.date(), _BUSINESS_END, tzinfo=WARSAW)
        available = (window_end - current).total_seconds() / 60
        if remaining <= available:
            return (current + timedelta(minutes=remaining)).astimezone(timezone.utc)
        remaining -= available
        current = _next_business_day_open(current.date())


def due_instants(priority: str, created_at: datetime) -> tuple[datetime, datetime]:
    """Apply C1 = wallclock: P1 on the wall-clock clock, P2-P4 on the business-hours clock."""
    ack_minutes, resolve_minutes = _TARGETS[priority]
    if priority == "P1":
        return wallclock_due(created_at, ack_minutes), wallclock_due(created_at, resolve_minutes)
    return business_hours_due(created_at, ack_minutes), business_hours_due(created_at, resolve_minutes)


def is_within_business_hours(now: datetime) -> bool:
    local = now.astimezone(WARSAW)
    if not _is_business_day(local.date()):
        return False
    return _BUSINESS_START <= local.time() < _BUSINESS_END


def breach_and_pause(ticket, now: datetime) -> dict:
    """docs/API.md section 5. `ticket` exposes priority, state and the timestamp/due fields as strings."""
    ack_due = parse_instant(ticket.ack_due_at)
    resolve_due = parse_instant(ticket.resolve_due_at)

    if ticket.acknowledged_at:
        ack_breached = parse_instant(ticket.acknowledged_at) > ack_due
    else:
        ack_breached = now > ack_due

    if ticket.resolved_at:
        resolve_breached = parse_instant(ticket.resolved_at) > resolve_due
    else:
        resolve_breached = now > resolve_due

    still_open = ticket.state not in ("resolved", "closed")
    on_business_clock = ticket.priority != "P1"  # C1 = wallclock: only P1 is exempt from pausing
    paused = still_open and on_business_clock and not is_within_business_hours(now)

    return {
        "priority": ticket.priority,
        "ack_due_at": ticket.ack_due_at,
        "resolve_due_at": ticket.resolve_due_at,
        "ack_breached": ack_breached,
        "resolve_breached": resolve_breached,
        "paused": paused,
    }
