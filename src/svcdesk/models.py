# ai-generated: 85% - Claude Code drafted the request/response shapes from docs/API.md section 2, reviewed by the author

"""The Ticket record (Ticket) and the request schema the API accepts (docs/API.md section 2)."""

from dataclasses import dataclass
from typing import Optional

from pydantic import BaseModel, Field


@dataclass
class Ticket:
    id: str
    title: str
    description: str
    reporter_name: str
    reporter_email: Optional[str]
    reporter_vip: bool
    impact: int
    urgency: int
    priority: str
    state: str
    related_to: Optional[str]
    created_at: str
    ack_due_at: str
    resolve_due_at: str
    acknowledged_at: Optional[str] = None
    resolved_at: Optional[str] = None
    closed_at: Optional[str] = None

    def to_response(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "reporter": {
                "name": self.reporter_name,
                "email": self.reporter_email,
                "vip": self.reporter_vip,
            },
            "impact": self.impact,
            "urgency": self.urgency,
            "priority": self.priority,
            "state": self.state,
            "created_at": self.created_at,
            "acknowledged_at": self.acknowledged_at,
            "resolved_at": self.resolved_at,
            "closed_at": self.closed_at,
            "related_to": self.related_to,
            "sla": {"ack_due_at": self.ack_due_at, "resolve_due_at": self.resolve_due_at},
        }


class ReporterIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: Optional[str] = None
    vip: bool = False


class TicketCreate(BaseModel):
    """Server-owned fields (id, priority, state, timestamps, sla) are simply absent from this model,
    so Pydantic silently drops them from an incoming request instead of rejecting it (R-20)."""

    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=4000)
    reporter: ReporterIn
    impact: int = Field(ge=1, le=3)
    urgency: int = Field(ge=1, le=3)
    related_to: Optional[str] = None
