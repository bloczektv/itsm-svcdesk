<!-- ai-generated: 70% - Claude Code drafted this specification from docs/REQUIREMENTS.md and docs/API.md; the three contradiction resolutions were proposed by Claude Code and reviewed by the author before this file was committed -->
# Feature Specification: svcdesk Ticketing API

**Feature Branch**: `001-svcdesk-ticketing`

**Created**: 2026-09-19

**Status**: Draft

**Input**: Build the service-desk API described in `docs/REQUIREMENTS.md` (R-01 to R-25) and
`docs/API.md`: an HTTP ticketing service that computes priority from impact and urgency, tracks tickets
through a fixed state machine, keeps SLA due instants on two possible clocks, and enforces a reopen window.
The requirements document contains three pairs of requirements that cannot both hold; this specification
resolves each pair and states which side is kept.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Raise and track a ticket (Priority: P1)

A desk agent or an integration raises a ticket for an IT issue, describing its impact and urgency. The
service computes the ticket's priority and the two SLA due instants immediately, and the ticket becomes
visible in the list and by direct lookup.

**Why this priority**: Without ticket creation and priority computation nothing else in the service has
meaning; this is the entire reason the desk exists (R-01, R-03, R-04, R-18).

**Independent Test**: `POST /tickets` with a valid body returns 201 with a computed `priority`, an `id`,
and an `sla` block; the ticket is then retrievable via `GET /tickets/{id}` and appears in `GET /tickets`.

**Acceptance Scenarios**:

1. **Given** no prior tickets, **When** a ticket is created with impact 1 and urgency 1, **Then** it is
   assigned priority `P1`, state `new`, a unique `id`, and SLA due instants computed from `created_at`.
2. **Given** a request missing `title`, **When** it is submitted, **Then** the service answers 400 or 422
   with a JSON `error` object and creates no ticket.

---

### User Story 2 - Move a ticket through its lifecycle (Priority: P2)

An agent acknowledges a new ticket, starts work on it, resolves it, and closes it once the reporter has
confirmed the fix. Every transition is a distinct, auditable action; shortcuts and actions in the wrong
order are refused.

**Why this priority**: The desk's core value is knowing the true state of every ticket; a state machine
that cannot be trusted makes every report wrong (R-07, R-08).

**Independent Test**: Drive one ticket through `new → acknowledged → in_progress → resolved → closed` via
its four action endpoints; each call returns 200 with the expected state and timestamp. A call from the
wrong state (for example `resolve` on a `new` ticket) returns 409.

**Acceptance Scenarios**:

1. **Given** a new ticket, **When** `POST /tickets/{id}/ack` is called, **Then** the ticket moves to
   `acknowledged` and `acknowledged_at` is set to the request's clock.
2. **Given** a resolved ticket, **When** `POST /tickets/{id}/resolve` is called again, **Then** the
   service answers 409 and the ticket is unchanged.

---

### User Story 3 - Reopen a ticket that did not stay fixed (Priority: P2)

A reporter whose issue recurs within the reopen window reopens the ticket rather than losing the history
in a new one. The window and its extent to closed tickets follow the resolution declared in
`DECISIONS.md` (C2).

**Why this priority**: A ticket that resurfaces and cannot be reopened either forces a disconnected new
record or silently reuses a closed one; both make the weekly report wrong (R-09, R-10, R-11).

**Independent Test**: Resolve a ticket, reopen it 6 days later (succeeds, `in_progress`), attempt to
reopen a different resolved ticket after 7 days and 1 second (fails, 409). Attempt to reopen a closed
ticket after 1 day: succeeds under this project's C2 = `immutable` resolution only from `resolved`, not
from `closed` (see Assumptions).

**Acceptance Scenarios**:

1. **Given** a ticket resolved 6 days ago, **When** it is reopened, **Then** it returns to `in_progress`
   and `resolved_at`/`closed_at` are cleared.
2. **Given** a ticket closed 1 day ago, **When** a reopen is attempted, **Then** the service answers 409
   (this project's C2 resolution: a closed ticket is immutable; the client creates a new ticket with
   `related_to`).

---

### User Story 4 - Read SLA status for the Monday report (Priority: P3)

Anyone producing the Monday report calls `GET /tickets/{id}/sla` for each open ticket to see whether the
acknowledgement or resolution target has been breached, and whether the ticket's clock is currently paused
for business hours.

**Why this priority**: This is the reporting payoff of the whole service (R-15, R-16); it depends on
Stories 1 and 2 already working, so it is correctly lower priority even though it is the desk's original
motivation.

**Independent Test**: Create a ticket with a fixed test clock in the past relative to its due instant,
call `/sla` with a later test clock, and confirm `ack_breached`/`resolve_breached`/`paused` match the
values published in `docs/API.md` §4 and §5 for the same test vector.

**Acceptance Scenarios**:

1. **Given** a P3 ticket created Friday afternoon and never acknowledged, **When** `/sla` is read the
   following Saturday, **Then** `paused` is `true`.
2. **Given** the same ticket, **When** `/sla` is read past its acknowledge-due instant, **Then**
   `ack_breached` is `true`.

### Edge Cases

- A request carries a malformed `X-Test-Clock` header (not RFC 3339): the service answers 400 or 422 and
  creates nothing.
- A client sends server-owned fields (`id`, `priority`, `state`, `sla`, ...) or unknown fields in a create
  request: they are silently ignored, never rejected (R-20).
- An action targets a ticket id that does not exist: 404 with a JSON `error` body, for every action
  endpoint and for `GET /tickets/{id}` and `GET /tickets/{id}/sla`.
- A P1 ticket's business-hours resolution target ends exactly at closing time (16:00 local): it is due at
  16:00 that day, not 08:00 the next business day (the tie rule, API.md §4, vector T4).
- A VIP reporter creates a ticket at impact 1, urgency 1: priority is `P1` under either C3 resolution (the
  VIP rule never lowers an already-maximal priority).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The service MUST expose `GET /health` returning 200 with `{"status": "ok", "service":
  "svcdesk"}` (R-02).
- **FR-002**: The service MUST accept `POST /tickets` with title (1-200 chars, required), optional
  description (up to 4000 chars), reporter name (1-100 chars, required), optional reporter email, optional
  `reporter.vip` (default false), required integer impact and urgency each in 1-3, and optional
  `related_to` (R-03).
- **FR-003**: The service MUST compute `priority` from impact and urgency via the fixed matrix in
  `docs/API.md` §3 and MUST ignore any `priority` value sent in the request body (R-04, R-05).
- **FR-004**: The service MUST raise a VIP reporter's ticket to at least `P2` regardless of the matrix
  result (this project's C3 = `vip` resolution of the C3 contradiction; see Assumptions) (R-06).
- **FR-005**: The service MUST enforce the state machine `new → acknowledged → in_progress → resolved →
  closed` with one action endpoint per transition (`/ack`, `/start`, `/resolve`, `/close`) and MUST refuse
  every other transition with 409 (R-07, R-08).
- **FR-006**: The service MUST refuse any action on an unknown ticket id with 404 (R-08).
- **FR-007**: The service MUST allow `POST /tickets/{id}/reopen` from a `resolved` ticket within 7 days of
  `resolved_at`, returning it to `in_progress` and clearing `resolved_at` and `closed_at` (R-10).
- **FR-008**: The service MUST refuse `reopen` from a `closed` ticket with 409 regardless of age (this
  project's C2 = `immutable` resolution of the C2 contradiction; see Assumptions) (R-09).
- **FR-009**: The service MUST refuse `reopen` outside the 7-day window with 409, and reopening MUST NOT
  change the ticket's original `resolve_due_at` (R-11).
- **FR-010**: The service MUST compute `ack_due_at` and `resolve_due_at` from `created_at` using the
  per-priority targets in `docs/API.md` §4, applying the wall-clock clock to P1 and the business-hours
  clock (Mon-Fri 08:00-16:00 Europe/Warsaw) to P2-P4 (this project's C1 = `wallclock` resolution of the C1
  contradiction; see Assumptions) (R-12, R-13, R-14).
- **FR-011**: `GET /tickets/{id}/sla` MUST report `priority`, `ack_due_at`, `resolve_due_at`,
  `ack_breached`, `resolve_breached`, and `paused`, computed at the request's clock, per the rules in
  `docs/API.md` §5 (R-15, R-16).
- **FR-012**: Every timestamp in every response MUST be an RFC 3339 instant in UTC with a `Z` suffix
  (R-17).
- **FR-013**: Every ticket MUST have an opaque, unique, non-empty server-assigned id that the client never
  chooses (R-18).
- **FR-014**: `GET /tickets` MUST list every ticket, honouring optional exact-match `state` and `priority`
  query filters, without pagination (R-19).
- **FR-015**: The service MUST reject a request that violates the field constraints of FR-002 with 400 or
  422 and a JSON body carrying a top-level `error` object (R-20).
- **FR-016**: When `SVCDESK_TEST_CLOCK` is `1` or `true`, the service MUST honour a per-request
  `X-Test-Clock` header as "now" for that request only, and MUST reject a header that does not parse as
  RFC 3339 with 400 or 422 (R-21).
- **FR-017**: The service MUST run as a Docker Compose service named `svcdesk`, built from this
  repository, listening on port 8080 inside the container, with no host-path bind mount and no network
  access required at runtime (R-22).
- **FR-018**: Tickets MUST survive a restart of the `svcdesk` container (R-23).
- **FR-019**: From `docker compose up`, the service MUST be running and `GET /health` MUST answer 200
  within 120 seconds (R-24).
- **FR-020**: An unknown path MUST answer 404 with a JSON body; an unknown ticket id MUST answer 404 with a
  JSON body carrying a top-level `error` object (R-25).

### Key Entities

- **Ticket**: the core record. Attributes: `id`, `title`, `description`, `reporter` (name, email, vip),
  `impact`, `urgency`, `priority` (derived), `state`, `created_at`, `acknowledged_at`, `resolved_at`,
  `closed_at`, `related_to`, `sla` (`ack_due_at`, `resolve_due_at`). Owns its own state-machine transitions
  and SLA computation; immutable once `closed` under this project's C2 resolution.
- **Reporter**: embedded in a ticket, not a standalone resource in Lab 1. Attributes: `name`, optional
  `email`, `vip` flag that can raise (never lower) the computed priority.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every one of the 49 published conformance checks in `docs/CHECKS.md` (L1-CORE-2) passes
  against the running service.
- **SC-002**: The service becomes ready (answers `GET /health` with 200) within 120 seconds of `docker
  compose up`.
- **SC-003**: All 8 published SLA test vectors (T1-T8 in `docs/API.md` §4) produce exactly the published
  due instants.
- **SC-004**: A ticket created, then the container restarted, is still retrievable afterward with its
  original id and data.
- **SC-005**: `DECISIONS.md`'s declared C1/C2/C3 values match, on every run, what the checker observes on
  the running service (L1-CORE-4).

## Assumptions

- **C1 (SLA clock for P1) = `wallclock`**: both P1 targets (acknowledge, resolve) use the wall-clock
  target `created_at + duration`, never paused by business hours; P2-P4 always use the business-hours
  clock. Rejects the business-hours half of R-13 as it would apply to P1; keeps R-14's "around the clock"
  requirement. Rationale: P1 means the whole organisation's work has stopped, and the requirements
  document itself frames P1 as unconditionally 24/7 ("a P1 raised on Friday evening is late at 15 minutes
  past, not on Monday morning").
- **C2 (closed tickets and reopening) = `immutable`**: `reopen` succeeds only from `resolved`, within 7
  days; a `closed` ticket always answers 409, and the client opens a new ticket with `related_to`. Rejects
  the "or closed" clause of R-10; keeps R-09's "a closed ticket is immutable" in full. Rationale: closed
  tickets are the historical record the Monday report is built from; letting them mutate after closure
  would make past reports silently wrong.
- **C3 (VIP reporters and the priority matrix) = `vip`**: after the matrix computes a priority, a VIP
  ticket at P3 or P4 is raised to P2; P1 and P2 are unchanged. Rejects the "and from nothing else" clause
  of R-05 for the VIP case; keeps R-06 in full. Rationale: R-06 states its own business purpose ("so that
  executive issues are visible to the desk immediately"), which is a standard, defensible escalation
  practice.
- Persistence uses SQLite in a named Docker volume; no external database is required for Lab 1 (R-23,
  `docs/API.md` §10).
- The checker never creates more than 100 tickets in one run (`docs/API.md` §1), so no pagination is
  required for `GET /tickets`.
- Polish public holidays are out of scope for business-hours computation for the whole course
  (`docs/API.md` §4).
