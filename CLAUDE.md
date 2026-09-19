<!-- ai-generated: 60% - Claude Code drafted this from the repository's own layout and docs/, reviewed by the author -->
# CLAUDE.md

Guidance for Claude Code sessions working in this repository.

## What this repository is

`svcdesk`: a service-desk ticketing API built for the ITSM 2026/27 course, Lab 1. The service and its
grading rules are entirely specified in `docs/API.md`, `docs/REQUIREMENTS.md` and `docs/CHECKS.md`; those
documents are the source of truth, never this file or any assumption made from prior labs.

## Ground rules for this repository

- **Specs before code.** `specs/` is written, pushed and receipted (`./itsmlab.ps1 submit 1 --kind specs`)
  before any file under `src/` (other than `src/README.md`) is committed. `L1-CORE-5` checks this from git
  history, not from good intentions.
- **`docs/API.md` wins.** Where `docs/REQUIREMENTS.md` and `docs/API.md` differ in precision, `docs/API.md`
  is the enforced contract.
- **`DECISIONS.md` must match the running service.** The three declared values (C1, C2, C3) are checked
  against what `itsmlab verify 1` actually observes (`L1-CORE-4`); if they ever diverge, fix the code or
  the declaration, never leave them inconsistent.
- **No network at container runtime, no bind mounts.** Every dependency is installed at build time;
  `docker-compose.yml` uses only named volumes.
- **The checker is the ground truth.** Run `./itsmlab.ps1 verify 1` after any change under `src/` or
  `DECISIONS.md`; do not trust a change by inspection alone.
- **Every source and spec file carries the `ai-generated:` disclosure header** in its first ten lines.

## Sub-agents

`.claude/agents/reviewer.md` is a narrow-scope reviewer with a `disallowedTools` denylist; see
`AGENT-POLICY.md` for why each entry is denied.
