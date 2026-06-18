# AE-0213 — Durable LangGraph checkpointer in prod (postgres) + startup guard

Status: Dev Complete
Tier: T2
Priority: Medium
Type: DevOps
Area: backend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-18
Updated: 2026-06-18

## Goal

Prod uses a durable (postgres) LangGraph checkpointer so workflow state survives restarts.

Source: Kaizen prod sweep `.agent/reports/kaizen-prod-2026-06-18.plan.md` (live carousel run, project b5b61790-9372-4a5a-ae17-30d2df28ef3d), validated by an independent architect cold-critic review.

## Problem

Prod runs `CAROUSEL_CHECKPOINT_BACKEND=memory` (verified). The in-memory checkpointer loses all workflow state on restart and isn't durable across processes, compounding resume fragility. The code already supports postgres (`bootstrap/app_factory.py:131-144`, which runs `.setup()` to create the checkpoint tables).

## Scope

- Set prod `CAROUSEL_CHECKPOINT_BACKEND=postgres` + `carousel_checkpoint_postgres_url` (GitHub Secret → deploy env).
- Add a startup validation that warns/fails when a non-durable backend (memory) is used outside dev.
- Confirm the checkpoint tables are created on first boot.

## Non-Goals

- Migrating existing in-memory state (none is durable to migrate).

## Acceptance Criteria

- [x] Startup guard rejects/warns on a non-durable backend outside dev. (Code: `bootstrap/startup_validation.py::validate_checkpointer_durability`, wired into `lifespan`.)
- [ ] Prod uses the postgres checkpointer; `checkpoint*` tables exist in prod DB. (DEPLOY action — ops must set `CAROUSEL_CHECKPOINT_BACKEND=postgres` + `CAROUSEL_CHECKPOINT_POSTGRES_URL` as deploy secrets; `_build_checkpointer` already runs `.setup()` to create the tables on first boot. Not code-completable here.)

## Gherkin Scenarios

```gherkin
Feature: ...

  Scenario: ...
    Given ...
    When ...
    Then ...
```

## Delta

### ADDED

- ...

### MODIFIED

- ...

### REMOVED

- ...

## Affected Areas

- Backend:
- Frontend:
- Database:
- API:
- Tests:
- Docs:
- Prompts/LLM:
- Observability:
- Deployment:

## Dependencies

- Blocks: —
- Blocked by: —
- Related: AE-0075 (checkpoint inventory)

## Implementation Plan

1. ...

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-18 HH:mm

Ticket created.

### 2026-06-18 dev

Implemented composition-root durable-checkpointer startup guard
(`bootstrap/startup_validation.py`), added `Settings.environment` +
`is_production_like`, wired into the app lifespan. Seeded tests pass; full
backend gates green (DB gates SKIP locally / verified separately). See
`.agent/reports/AE-0213.dev-summary.md`.

## Files Touched

- `backend/src/rag_backend/infrastructure/config/settings.py`
- `backend/src/rag_backend/infrastructure/config/constants.py` (new)
- `backend/src/rag_backend/bootstrap/startup_validation.py` (new)
- `backend/src/rag_backend/bootstrap/app_factory.py`
- `backend/.env.example`
- `backend/tests/features/startup_hardening.feature` (new)
- `backend/tests/unit/bootstrap/test_startup_validation.py` (new)

## Test Evidence

```bash
uv run pytest tests/unit/bootstrap/ -q
# 8 passed
```

Seeded tests (AE-0213 portion):
- `test_prod_memory_checkpointer_raises` — prod + memory → StartupValidationError.
- `test_prod_disabled_checkpointer_raises` — prod + disabled → StartupValidationError.
- `test_prod_postgres_checkpointer_passes` — prod + postgres → pass.
- `test_dev_memory_checkpointer_warns_not_raises` — dev + memory → warn (no raise).
- `test_staging_is_production_like_for_checkpointer` — staging fails fast.

Gates: `GATES_JSON: {"pass":14,"fail":0,"skip":3,...}` (test/diff-cover verified
PASS with DATABASE_URL set; migrations SKIP — no models touched). Integrity: 0
net-new blockers. arch-ratchet PASS (import ratchets flat).

## QA Report

Pending.

## Decision Log

Pending.

## Blockers

None.

## Final Summary

Pending.
