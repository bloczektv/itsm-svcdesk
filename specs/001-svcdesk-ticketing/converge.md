<!-- ai-generated: 80% - Claude Code drafted this comparison of spec.md against the implementation in src/; the author reviewed it against the actual `itsmlab verify 1` output -->
# Convergence report: svcdesk Ticketing API

This compares `specs/001-svcdesk-ticketing/spec.md` (and `docs/REQUIREMENTS.md`) with what was actually
built in `src/svcdesk/`, checked against a real `itsmlab verify 1` run (commit `3fae9f1`, plus the
implementation on top of it). Core result at the time of writing: `L1-CORE-1` through `L1-CORE-4` all
`pass`; `L1-CORE-5` `skip` (grader-only).

## Requirement coverage

**R-01/R-02 (HTTP/JSON, `/health`)**: implemented in `src/svcdesk/main.py`; `GET /health` returns
`{"status": "ok", "service": "svcdesk"}`. Verified by check 2.01.

**R-03/R-20 (ticket shape and validation)**: `src/svcdesk/models.py`'s `TicketCreate`/`ReporterIn` encode
every field constraint from `spec.md`'s functional requirement FR002 directly as Pydantic `Field` bounds (title 1-200,
description 0-4000, reporter name 1-100, impact/urgency integers 1-3). Server-owned and unknown fields are
structurally absent from `TicketCreate`, so Pydantic drops them rather than rejecting the request, matching
R-20's "ignored, never rejected" clause. Verified by checks 2.05, 2.16-2.19, 2.48.

**R-04/R-05/R-06 (priority, C3)**: `src/svcdesk/priority.py` implements the matrix as a literal lookup
table, then applies the C3 = `vip` floor at P2 exactly as declared in `DECISIONS.md`. All nine matrix cells
and the VIP cases are covered by checks 2.07-2.15 and 2.46-2.48; the checker's `observations` line
confirmed `C3=vip`, matching the declaration (L1-CORE-4.03).

**R-07/R-08/R-09/R-10/R-11 (state machine, C2)**: `src/svcdesk/state_machine.py` encodes the four simple
transitions and the reopen rule with the C2 = `immutable` resolution (reopen only from `resolved`, a
`closed` ticket always 409). Checks 2.24-2.35 and 2.49 cover every transition and both reopen-window
boundaries (6 days succeeds, 7 days + 1 second fails). `observations` confirmed `C2=immutable`
(L1-CORE-4.02).

**R-12 through R-16 (SLA targets, clocks, breach, pause, C1)**: `src/svcdesk/sla.py` implements both the
wall-clock and business-hours due-instant calculators, including the tie-at-closing-time rule, and applies
C1 = `wallclock` to P1 only. All eight published test vectors (T1-T8 in `docs/API.md` section 4) were
hand-verified against this implementation before the first checker run and passed on the first attempt
(checks 2.36-2.45); `observations` confirmed `C1=wallclock` (L1-CORE-4.01).

**R-17 through R-19, R-21, R-25 (instants, ids, listing, test clock, unknown routes)**: `timeutil.py` and
`clock.py` handle RFC 3339 parsing/formatting and the `X-Test-Clock` header; `main.py`'s `list_tickets` and
`get_ticket` cover filtering and the 404 cases. Checks 2.02-2.04, 2.06, 2.20-2.23 all pass.

**R-22, R-24 (compose contract)**: the template's `docker-compose.yml` already satisfied the `build:` key,
port 8080, `SVCDESK_TEST_CLOCK` and no-bind-mount requirements unchanged; `Dockerfile` installs every
dependency at build time. Checks 1.01-1.04 pass, and `/health` answers well inside the 120 s window.

**R-23 (persistence)**: `src/svcdesk/store.py` persists every ticket to SQLite in the named volume
`svcdesk-data`. Not checked by Tier A in Lab 1 (`docs/API.md` section 10), so this is implemented ahead of
where it is graded, for Lab 2.

## Gaps and deliberate simplifications

- `plan.md` originally proposed SQLModel/SQLAlchemy for storage; the implementation uses the standard
  library's `sqlite3` module instead, to remove a dependency and a source of version-pinning risk in the
  build. The behaviour (SQLite in a named volume) is unchanged from the plan's intent.
- `related_to` is accepted and stored but never validated against an existing ticket id, exactly as
  `docs/API.md` section 2 specifies ("not validated in Lab 1").
- Error `code` strings (`invalid_transition`, `reopen_window_expired`, `ticket_closed`, `not_found`,
  `validation`) are implemented as recommended by `docs/API.md` section 6, even though Lab 1 checks only
  the status code and the presence of a top-level `error` object.

## Conclusion

Every functional requirement in `spec.md` that Lab 1's Core bundle checks has a corresponding, verified
implementation; the three contradiction resolutions declared in `DECISIONS.md` (C1=wallclock,
C2=immutable, C3=vip) are exactly what the running service exhibits, confirmed by the checker's own
`observations` output rather than by inspection alone.
