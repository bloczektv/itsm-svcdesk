# svcdesk Constitution

## Core Principles

### I. Contract Fidelity
`docs/API.md` is the single source of truth for the HTTP interface. Every endpoint, status code, field
name and SLA calculation MUST match it exactly. Where `docs/REQUIREMENTS.md` and `docs/API.md` differ in
precision, `docs/API.md` wins. The service speaks only HTTP and JSON (`application/json`); there is no
other interface.

### II. Specs Before Code (NON-NEGOTIABLE)
The specification under `specs/` is written and pushed before any file under `src/` exists. This is not a
style preference: the grader's `L1-CORE-5` check verifies it structurally from commit ancestry. No code is
written until the `specs` receipt exists.

### III. Decisions Are Explicit and Defended
The requirements document contains three pairs of requirements that cannot both hold (SLA clock for P1,
closed-ticket reopening, VIP priority override). Each pair is resolved by deliberately rejecting the
minimal conflicting part of one requirement, and the resolution actually implemented by the running
service is declared and defended in `DECISIONS.md`. The declared values MUST equal what the service does;
a mismatch is a defect, not a documentation nit.

### IV. Test-First Against Published Vectors
`docs/API.md` §4 publishes exact SLA test vectors (T1-T8) and `docs/CHECKS.md` publishes every check the
grader runs, by id. Implementation work is driven by these fixed, deterministic inputs: a change is not
done until the checker (`itsmlab verify 1`) reports the corresponding check as `pass`.

### V. No Runtime Network, No Bind Mounts
The image installs every dependency at build time; the grading sandbox has no egress once images are
built. No service in `docker-compose.yml` uses a host-path bind mount, in any override file or through
`.env`. Persistence uses a named volume.

## Technology Constraints

Python 3.13 with FastAPI, packaged with a `build:` key in `docker-compose.yml` (never `image:` alone),
listening on `0.0.0.0:8080` inside the container. The image includes the IANA time zone database
(Debian-based `python:3.13-slim` ships it) because every SLA calculation for non-P1 priorities, and for P1
under the `business` resolution, depends on `Europe/Warsaw` business hours. Storage is SQLite in a named
volume so tickets survive a container restart.

## Development Workflow

Order of work: constitution → specification (`specs/`) → push → specs receipt → `DECISIONS.md` → plan →
tasks → implementation (`src/`) → local verification loop (`itsmlab verify 1`) until every Core spec
passes → commit → tag → submission receipt. Every source and specification file carries the
`ai-generated: <0-100>% - <how>` disclosure header in its first ten lines. Local checker runs are
unlimited and are run as often as needed; only tagged, receipted attempts count toward the grade.

## Governance

This constitution governs the Lab 1 `svcdesk` build. Amendments are made by editing this file and noting
the change in the commit message; there is no separate approval body for a single-student lab project.
Every implementation decision defers to `docs/API.md` and `docs/CHECKS.md` first, this constitution
second, and `docs/REQUIREMENTS.md` for intent and rationale.

**Version**: 1.0.0 | **Ratified**: 2026-09-19 | **Last Amended**: 2026-09-19
