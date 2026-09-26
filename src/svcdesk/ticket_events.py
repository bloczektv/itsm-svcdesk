# ai-generated: 85% - Claude Code drafted the implementation against METRIC-SPEC.md section 7, reviewed by the author

"""GET /dora/ticket-events: every ticket's lifecycle instants, as the stream Lab 7 will load."""

from . import store

_PHASES = (
    ("created_at", "created", "new"),
    ("acknowledged_at", "acknowledged", "acknowledged"),
    ("resolved_at", "resolved", "resolved"),
    ("closed_at", "closed", "closed"),
)


def build_stream() -> list:
    events = []
    for ticket in store.list_all():
        for attr, phase, state in _PHASES:
            at = getattr(ticket, attr)
            if at is not None:
                events.append({
                    "ticket_id": ticket.id,
                    "at": at,
                    "phase": phase,
                    "priority": ticket.priority,
                    "state": state,
                })
    events.sort(key=lambda e: (e["at"], e["ticket_id"]))
    return events
