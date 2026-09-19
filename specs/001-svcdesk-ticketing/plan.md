<!-- ai-generated: 80% - Claude Code drafted this plan from spec.md and docs/API.md; the author reviewed the technology and structure choices -->
# Implementation Plan: svcdesk Ticketing API

**Branch**: `001-svcdesk-ticketing` | **Date**: 2026-09-19 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-svcdesk-ticketing/spec.md`

## Summary

Build an HTTP ticketing service (`svcdesk`) that creates and drives tickets through a fixed state machine,
computes priority from an impact/urgency matrix with a VIP override, and tracks two SLA due instants per
ticket on either a wall-clock or a business-hours clock, exactly as specified in `docs/API.md`. The
approach: a single FastAPI application, an in-process priority/SLA calculator with no external service
dependencies, and SQLite (via SQLModel) in a named Docker volume for persistence.

## Technical Context

**Language/Version**: Python 3.13

**Primary Dependencies**: FastAPI, Uvicorn, SQLModel (SQLAlchemy + Pydantic), Pydantic v2

**Storage**: SQLite file in the named volume `svcdesk-data` (mounted at `/data`, never a bind mount)

**Testing**: pytest + httpx (FastAPI `TestClient`) for unit/contract tests during development; the
authoritative conformance test is the course checker (`itsmlab verify 1`) against `docs/CHECKS.md`

**Target Platform**: Linux container (`python:3.13-slim`), amd64 and arm64 (multi-arch base image)

**Project Type**: single web service (no frontend)

**Performance Goals**: no explicit throughput target in Lab 1; the checker creates at most 100 tickets per
run and every HTTP request has a 10 s timeout budget

**Constraints**: no network access at container runtime (all dependencies installed at build time); no
host-path bind mounts; `GET /health` must answer within 120 s of `docker compose up`; peak container RAM
about 0.4 GB

**Scale/Scope**: single service, 8 endpoints, one entity (Ticket)

## Constitution Check

*Gate: re-checked after this plan.*

- **Contract Fidelity**: every endpoint, field and status code below is taken directly from `docs/API.md`
  sections 1-9; no field or route is invented. PASS.
- **Specs Before Code**: this plan and the parent spec live entirely under `specs/`; nothing under `src/`
  is touched by this document. PASS.
- **Decisions Are Explicit and Defended**: the C1/C2/C3 resolutions from `spec.md`'s Assumptions section
  are threaded through the priority and SLA calculators below (FR-004, FR-008, FR-010) and will be restated
  in `DECISIONS.md` before implementation is tagged. PASS (pending the author's sign-off on the three
  values before the submission tag).
- **Test-First Against Published Vectors**: the SLA calculator's test suite is the 8 vectors T1-T8 of
  `docs/API.md` §4, asserted byte-for-byte against the published instants. PASS.
- **No Runtime Network, No Bind Mounts**: `requirements.txt` is fully resolved and installed in the
  Docker build stage; `docker-compose.yml` uses the named volume `svcdesk-data`. PASS.

No violations; the Complexity Tracking table is omitted.

## Project Structure

### Documentation (this feature)

```text
specs/001-svcdesk-ticketing/
├── spec.md                 # feature specification (done)
├── plan.md                 # this file
├── tasks.md                # Phase 2 output
└── checklists/
    └── requirements.md     # spec quality checklist (done)
```

### Source Code (repository root)

```text
src/
├── main.py              # FastAPI app, route registration, exception handlers
├── models.py             # SQLModel Ticket table + Pydantic request/response schemas
├── priority.py           # impact/urgency matrix + VIP override (C3)
├── sla.py                # wall-clock and business-hours due-instant calculators (C1); breach/pause (R-16)
├── state_machine.py      # transition table, reopen-window rule (C2)
├── clock.py              # X-Test-Clock header parsing, SVCDESK_TEST_CLOCK gate (R-21)
├── db.py                 # SQLite engine/session setup against the named volume
└── requirements.txt

Dockerfile                # FROM python:3.13-slim, tzdata already present, no RUN that needs network at start
docker-compose.yml         # service svcdesk, build:, port 8080, SVCDESK_TEST_CLOCK=1, named volume
```

**Structure Decision**: single project under `src/`, no `tests/` package for Lab 1 Core (pytest is used
ad hoc during development; a `tests` Compose service for Stretch S3, if attempted, lives under
`src/tests_own/` and is added later without touching this structure).

## Module responsibilities

- **`clock.py`**: resolves "now" for a request — the parsed `X-Test-Clock` header when
  `SVCDESK_TEST_CLOCK` is truthy and the header is present and valid, else real UTC time; raises a
  validation error for a header that does not parse (R-21, FR-016).
- **`priority.py`**: pure function `(impact, urgency, vip) -> priority`, matrix lookup then the C3 VIP
  floor at P2 (FR-003, FR-004).
- **`sla.py`**: pure functions `wallclock_due(created_at, target)` and
  `business_hours_due(created_at, target)` (Europe/Warsaw, the tie-at-closing rule), plus
  `due_instants(priority, created_at)` that applies C1 (P1 wall-clock, P2-P4 business-hours) and
  `breach_and_pause(ticket, now)` (R-16, FR-010, FR-011).
- **`state_machine.py`**: the transition table of `docs/API.md` §6 plus the C2 reopen rule (resolved only
  from `resolved`) and the 7-day window check (FR-005 through FR-009).
- **`models.py`**: the `Ticket` table and the request/response Pydantic models, with server-owned fields
  excluded from the create-request model so they are structurally impossible to set from the client
  (FR-002, FR-013, R-20).
- **`main.py`**: wires the above into the 8 routes of `docs/API.md` §1, the 400/404/409/422 error
  responses with a top-level `error` object, and the `/health` route.
