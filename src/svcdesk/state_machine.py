# ai-generated: 85% - Claude Code drafted against docs/API.md section 6, reviewed by the author

"""State machine and reopen window (docs/API.md section 6).

C2 = immutable (DECISIONS.md): reopen succeeds only from `resolved`, within 7 days; a `closed`
ticket always answers 409 and the client opens a new ticket with `related_to`.
"""

from datetime import datetime, timedelta

from .exceptions import Conflict
from .timeutil import fmt_instant, parse_instant

C2_RESOLUTION = "immutable"  # matches DECISIONS.md; the other admissible value is "reopen"

REOPEN_WINDOW = timedelta(days=7)

# action -> (required current state, new state, timestamp field set to `now`, or None)
_SIMPLE_TRANSITIONS = {
    "ack": ("new", "acknowledged", "acknowledged_at"),
    "start": ("acknowledged", "in_progress", None),
    "resolve": ("in_progress", "resolved", "resolved_at"),
    "close": ("resolved", "closed", "closed_at"),
}


def apply_action(ticket, action: str, now: datetime) -> None:
    """Mutate `ticket` in place, or raise Conflict (409) for an invalid transition."""
    if action in _SIMPLE_TRANSITIONS:
        from_state, to_state, ts_field = _SIMPLE_TRANSITIONS[action]
        if ticket.state != from_state:
            raise Conflict("invalid_transition", f"cannot {action} a ticket in state '{ticket.state}'")
        ticket.state = to_state
        if ts_field:
            setattr(ticket, ts_field, fmt_instant(now))
        return

    if action == "reopen":
        if ticket.state == "resolved":
            if now <= parse_instant(ticket.resolved_at) + REOPEN_WINDOW:
                _reopen(ticket)
                return
            raise Conflict("reopen_window_expired", "reopen window (7 days from resolved_at) has expired")

        if ticket.state == "closed":
            if C2_RESOLUTION == "reopen" and now <= parse_instant(ticket.closed_at) + REOPEN_WINDOW:
                _reopen(ticket)
                return
            code = "reopen_window_expired" if C2_RESOLUTION == "reopen" else "ticket_closed"
            raise Conflict(code, "a closed ticket is immutable; open a new ticket with related_to")

        raise Conflict("invalid_transition", f"cannot reopen a ticket in state '{ticket.state}'")

    raise ValueError(f"unknown action {action!r}")


def _reopen(ticket) -> None:
    ticket.state = "in_progress"
    ticket.resolved_at = None
    ticket.closed_at = None
