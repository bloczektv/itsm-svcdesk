# ai-generated: 85% - Claude Code drafted the route wiring against docs/API.md sections 1, 7 and 9; reviewed by the author

"""svcdesk: the service-desk ticketing API (docs/API.md is the source of truth for every shape below)."""

import uuid
from contextlib import asynccontextmanager

from fastapi import Body, FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from . import dora, store, ticket_events
from .clock import resolve_now
from .exceptions import ApiError, NotFound
from .models import Ticket, TicketCreate
from .priority import compute_priority
from .sla import breach_and_pause, due_instants
from .state_machine import apply_action
from .timeutil import fmt_instant


@asynccontextmanager
async def lifespan(app: FastAPI):
    store.init_db()
    yield


app = FastAPI(title="svcdesk", lifespan=lifespan)


@app.exception_handler(ApiError)
async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"error": {"code": exc.code, "message": exc.message}})


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    first = exc.errors()[0] if exc.errors() else {"msg": "validation error"}
    return JSONResponse(status_code=422, content={"error": {"code": "validation", "message": first["msg"]}})


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "svcdesk"}


@app.post("/tickets", status_code=201)
def create_ticket(payload: TicketCreate, request: Request) -> dict:
    now = resolve_now(request)
    priority = compute_priority(payload.impact, payload.urgency, payload.reporter.vip)
    ack_due, resolve_due = due_instants(priority, now)
    ticket = Ticket(
        id=str(uuid.uuid4()),
        title=payload.title,
        description=payload.description,
        reporter_name=payload.reporter.name,
        reporter_email=payload.reporter.email,
        reporter_vip=payload.reporter.vip,
        impact=payload.impact,
        urgency=payload.urgency,
        priority=priority,
        state="new",
        related_to=payload.related_to,
        created_at=fmt_instant(now),
        ack_due_at=fmt_instant(ack_due),
        resolve_due_at=fmt_instant(resolve_due),
    )
    store.save(ticket)
    return ticket.to_response()


@app.get("/tickets")
def list_tickets(state: str | None = Query(default=None), priority: str | None = Query(default=None)) -> list:
    return [t.to_response() for t in store.list_all(state=state, priority=priority)]


@app.get("/tickets/{ticket_id}")
def get_ticket(ticket_id: str) -> dict:
    ticket = store.get(ticket_id)
    if ticket is None:
        raise NotFound(f"no ticket with id {ticket_id!r}")
    return ticket.to_response()


@app.get("/tickets/{ticket_id}/sla")
def get_sla(ticket_id: str, request: Request) -> dict:
    ticket = store.get(ticket_id)
    if ticket is None:
        raise NotFound(f"no ticket with id {ticket_id!r}")
    now = resolve_now(request)
    return breach_and_pause(ticket, now)


def _act(ticket_id: str, action: str, request: Request) -> dict:
    ticket = store.get(ticket_id)
    if ticket is None:
        raise NotFound(f"no ticket with id {ticket_id!r}")
    now = resolve_now(request)
    apply_action(ticket, action, now)
    store.save(ticket)
    return ticket.to_response()


@app.post("/tickets/{ticket_id}/ack")
def ack_ticket(ticket_id: str, request: Request) -> dict:
    return _act(ticket_id, "ack", request)


@app.post("/tickets/{ticket_id}/start")
def start_ticket(ticket_id: str, request: Request) -> dict:
    return _act(ticket_id, "start", request)


@app.post("/tickets/{ticket_id}/resolve")
def resolve_ticket(ticket_id: str, request: Request) -> dict:
    return _act(ticket_id, "resolve", request)


@app.post("/tickets/{ticket_id}/close")
def close_ticket(ticket_id: str, request: Request) -> dict:
    return _act(ticket_id, "close", request)


@app.post("/tickets/{ticket_id}/reopen")
def reopen_ticket(ticket_id: str, request: Request) -> dict:
    return _act(ticket_id, "reopen", request)


@app.post("/dora/metrics")
def dora_metrics(payload: dict = Body(...)) -> dict:
    return dora.compute_metrics(payload)


@app.get("/dora/ticket-events")
def dora_ticket_events() -> list:
    return ticket_events.build_stream()
