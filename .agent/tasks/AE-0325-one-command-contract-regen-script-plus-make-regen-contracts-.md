# AE-0325 — one-command contract regen script plus make regen-contracts with read-only verify pass

Status: Dev Complete
Tier: T1
Priority: Medium
Type: Quality
Area: backend
Owner: Unassigned
Branch: feat/kaizen-wave-ae0322-0328
Created: 2026-07-22
Updated: 2026-07-22

## Goal

`make regen-contracts` regenerates all four pinned contract artifacts in one
fail-fast command and only exits 0 after a read-only verification pass proves
they are consistent.

## Problem

Kaizen failure class FC-5 (`.agent/reports/kaizen-session-2026-07-22.signal.md`).
Every API-contract change requires four separate regenerations — the OpenAPI
export (`docs/architecture/openapi.json` via `backend/scripts/export_openapi.py`),
the route snapshot (`REGEN_ROUTE_SNAPSHOT=1`), and the publishing + editorial
workflow snapshot tests (`--snapshot-update`) — each typically rediscovered via
its own red gate (PR #80 wave hit all of them, learnings-log 2026-07-01). The
recipe lives only in agent memory, not the repo (verified 2026-07-22: no script
or Makefile target). Bonus landmine: `export_openapi.py` loads `.env` from CWD,
so running it from repo root fails on the root `.env`'s `ENCRYPTION_KEY`.

## Scope

- `scripts/dev/regen_contracts.sh`: `set -euo pipefail`; cd's into `backend/`
  itself (killing the CWD/.env landmine); runs the four regen steps in order;
  aborts on the FIRST failure with a clear "regen INCOMPLETE — artifacts may be
  inconsistent" banner.
- Final step: re-run the four snapshot/contract checks **read-only** (no
  `--snapshot-update`, no regen env vars) and exit 0 only when all verify green
  (cold-critic WARN-5: a half-updated state must not look done).
- `Makefile` target `regen-contracts`; short doc in `docs/guides/` linked from
  backend commands docs.

## Non-Goals

- No change to the pinned gates themselves — they remain the commit-time
  enforcers; this only removes regen friction.
- Do not auto-run on commit or in CI.

## Acceptance Criteria

- [x] `make regen-contracts` regenerates all four artifacts from a clean state
      and exits 0 with a final read-only verification pass green.
- [x] Seeded failure test (AE-0180): with one regen step forced to fail (e.g.
      unimportable app / broken test), the script exits non-zero, prints the
      INCOMPLETE banner, and does not report success.
- [x] Script works from any CWD (explicitly cd's; no dependence on the caller's
      directory or root `.env`).
- [x] Doc page lists the four artifacts and when regen is required, replacing
      tribal knowledge.

## Repro Steps

1. Change any API schema/route.
2. Today: four separate gates go red one after another; the regen commands must
   be recalled from memory, and `export_openapi.py` fails when run from repo
   root.

## Affected Areas

- [x] Backend
- [ ] Frontend
- [x] Tests

## Dependencies

None.

## Decision Log

- Cold-critic WARN-5 (2026-07-22): bundling regen can hide partial failures.
  Resolved: fail-fast + mandatory read-only verify pass before exit 0.

## Progress Log

### 2026-07-22 — development complete (wave feat/kaizen-wave-ae0322-0328)

Implemented: scripts/dev/regen_contracts.sh (set -euo pipefail + ERR trap banner, cds into backend/ killing the .env landmine, 4 regen steps + read-only verify of all four), make regen-contracts, docs/guides/api-contract-regen.md linked from backend CLAUDE.md. Commit ac281fd4.

### 2026-07-22

Ticket created by kaizen session-2026-07-22 (proposal P5). Plan:
`.agent/reports/kaizen-session-2026-07-22.plan.md`.

## Files Touched

- scripts/dev/regen_contracts.sh
- Makefile
- docs/guides/api-contract-regen.md
- backend/tests/unit/scripts_ci/test_regen_contracts.py
- backend/CLAUDE.md

## Test Evidence

uv run pytest tests/unit/scripts_ci/test_regen_contracts.py -> 5 passed (seeded step failure -> INCOMPLETE banner + fail-fast at call N; green run -> read-only verify pass + exit 0; verify-phase failure -> INCOMPLETE; CWD-independent). Real end-to-end run: bash scripts/dev/regen_contracts.sh -> exit 0, all 4 artifacts regenerated + verified read-only, zero git diff (byte-idempotent).

## QA Report

Pending.

## Blockers

None.
