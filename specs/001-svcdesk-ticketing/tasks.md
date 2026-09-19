<!-- ai-generated: 80% - Claude Code drafted this task breakdown from plan.md; the author reviewed the ordering and scope -->
# Tasks: svcdesk Ticketing API

**Input**: Design documents from `specs/001-svcdesk-ticketing/` (spec.md, plan.md)

**Tests**: pytest tests are written alongside `sla.py` and `state_machine.py` because those modules encode
published, checkable vectors (T1-T8) and a fixed transition table; the checker (`itsmlab verify 1`) is the
authoritative acceptance test for every task below and is run after each phase.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can be done in parallel (different files, no dependency on another unfinished task)
- **[Story]**: which user story (spec.md) the task serves

## Phase 1: Setup (Shared Infrastructure)

- [ ] T001 Write `Dockerfile` from `Dockerfile.example`: `FROM python:3.13-slim`, `COPY src/requirements.txt`, `pip install --no-cache-dir -r requirements.txt`, `COPY src/ .`, `CMD` runs uvicorn on `0.0.0.0:8080`
- [ ] T002 Write `src/requirements.txt`: fastapi, uvicorn[standard], sqlmodel, pydantic
- [ ] T003 [P] Update `docker-compose.yml`: service `svcdesk` with `build: .`, `"8080:8080"`, `SVCDESK_TEST_CLOCK: "1"`, named volume `svcdesk-data:/data`, no bind mounts
- [ ] T004 [P] `src/db.py`: SQLite engine pointed at `/data/svcdesk.db`, session dependency for FastAPI

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: everything every user story needs; no story starts before this phase is green.

- [ ] T005 `src/clock.py`: `resolve_now(request) -> datetime`, honouring `SVCDESK_TEST_CLOCK` and `X-Test-Clock` (R-21); raises on an unparsable header
- [ ] T006 `src/models.py`: `Ticket` SQLModel table (all fields per API.md §2) and the `TicketCreate` /
      `TicketRead` Pydantic schemas (server-owned fields absent from `TicketCreate`)
- [ ] T007 [P] `src/priority.py`: matrix lookup + C3 VIP-floor-at-P2 function, with a unit test covering
      all 9 matrix cells plus the VIP cases (2.07-2.15, 2.46-2.48 of CHECKS.md)
- [ ] T008 [P] `src/sla.py`: `wallclock_due`, `business_hours_due` (Europe/Warsaw, tie-at-closing rule),
      `due_instants` (applies C1), `breach_and_pause`; unit test asserting all 8 vectors T1-T8 verbatim
- [ ] T009 [P] `src/state_machine.py`: transition table + C2 reopen rule (`resolved` only, 7-day window);
      unit test covering every edge in API.md §6 including the two 409 boundary cases (6 days / 7 days+1s)
- [ ] T010 `src/main.py` skeleton: FastAPI app, `GET /health`, global exception handlers producing the
      `{"error": {...}}` body shape for 400/404/409/422

**Checkpoint**: `docker compose build && docker compose up svcdesk` starts and `/health` returns 200.

## Phase 3: User Story 1 - Raise and track a ticket (P1) 🎯 MVP

**Goal**: `POST /tickets`, `GET /tickets`, `GET /tickets/{id}`, validation, computed priority and SLA block.

- [ ] T011 [US1] `POST /tickets` in `src/main.py`: validate via `TicketCreate`, call `priority.py` and
      `sla.py`, persist, return 201 with the full ticket (2.03, 2.05, 2.06)
- [ ] T012 [US1] Validation errors → 400/422 with `{"error": {...}}` for missing title, bad impact/urgency,
      overlong title (2.16-2.19)
- [ ] T013 [US1] `GET /tickets/{id}` → 200 or 404 with `{"error": {...}}` (2.20, 2.21)
- [ ] T014 [US1] `GET /tickets` with optional `?state=` and `?priority=` exact-match filters (2.22, 2.23)
- [ ] T015 [US1] `GET /this-route-does-not-exist` and any unknown path → 404 JSON body (2.02, R-25)

**Checkpoint**: run `./itsmlab.ps1 verify 1` — L1-CORE-1 and the creation/read checks of L1-CORE-2 pass.

## Phase 4: User Story 2 - Move a ticket through its lifecycle (P2)

- [ ] T016 [US2] `POST /tickets/{id}/ack` — `new → acknowledged`, sets `acknowledged_at` (2.24)
- [ ] T017 [US2] `POST /tickets/{id}/start` — `acknowledged → in_progress` (2.27)
- [ ] T018 [US2] `POST /tickets/{id}/resolve` — `in_progress → resolved`, sets `resolved_at` (2.28)
- [ ] T019 [US2] `POST /tickets/{id}/close` — `resolved → closed`, sets `closed_at` (2.30)
- [ ] T020 [US2] Every action wires through `state_machine.py`: any other transition → 409; unknown id →
      404 (2.25, 2.26, 2.29, 2.31, 2.49)

**Checkpoint**: full lifecycle checks of L1-CORE-2 pass (2.24-2.31, 2.49).

## Phase 5: User Story 3 - Reopen within the window (P2)

- [ ] T021 [US3] `POST /tickets/{id}/reopen` wired to `state_machine.py`'s C2 rule: `resolved` within 7
      days → `in_progress`, clearing `resolved_at`/`closed_at`; `closed` → always 409 under C2 = `immutable`
      (2.32, 2.33, 2.34, 2.35)

**Checkpoint**: reopen checks of L1-CORE-2 pass (2.32-2.35).

## Phase 6: User Story 4 - SLA status for the Monday report (P3)

- [ ] T022 [US4] `GET /tickets/{id}/sla` — returns `priority, ack_due_at, resolve_due_at, ack_breached,
      resolve_breached, paused` via `sla.breach_and_pause` (2.36-2.45)
- [ ] T023 [US4] Verify the C1 boundary check (T3, vector 2.41: either admissible pair, matching the
      declared C1) end-to-end through the running service

**Checkpoint**: all SLA checks of L1-CORE-2 pass (2.36-2.45), including 2.41 and the shared-T2-ticket
checks 2.42/2.43/2.45.

## Phase 7: Persistence & Polish

- [ ] T024 [P] Verify tickets survive `docker compose restart svcdesk` (R-23, SC-004)
- [ ] T025 [P] Add the `ai-generated:` header to every file under `src/` that lacks one
- [ ] T026 Run `./itsmlab.ps1 verify 1` clean; fix any remaining `fail`/`error` rows until Core is green
- [ ] T027 Write `DECISIONS.md` (front matter + three sections, five labels each) matching the C1/C2/C3
      values actually observed in the `verify 1` output's `observations` line (L1-CORE-3, L1-CORE-4)

## Dependencies & Execution Order

- Phase 1 (Setup) → Phase 2 (Foundational) blocks every user story.
- Phase 3 (US1) has no dependency on US2-US4 and is the MVP checkpoint.
- Phase 4 (US2) depends on US1 existing (tickets must be creatable to be transitioned).
- Phase 5 (US3) depends on US2 (`resolved`/`closed` states must exist to reopen).
- Phase 6 (US4) depends on US1 (SLA block is computed at creation) but not on US2/US3.
- Phase 7 runs last and requires all prior phases green.

## Notes

- T007, T008, T009 are parallelizable (different files, no shared state).
- Every phase checkpoint is "run `itsmlab verify 1`", not "trust the code by inspection" — the checker is
  the ground truth for every check id cited above.
- DECISIONS.md (T027) is written last so its declared values are guaranteed to match the running service,
  never the other way around.
