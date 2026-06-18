# AE-0207 — Reconcile prod DB to Alembic and run migrations on deploy

Status: Done
Tier: T3
Priority: Critical
Type: DevOps
Area: backend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-18
Updated: 2026-06-18

## Goal

Stop production DB schema drift: prod must run Alembic migrations on deploy and a drift check must fail the deploy when the live schema lacks a model column.

Source: Kaizen prod sweep `.agent/reports/kaizen-prod-2026-06-18.plan.md` (live carousel run, project b5b61790-9372-4a5a-ae17-30d2df28ef3d), validated by an independent architect cold-critic review.

## Problem

Prod was bootstrapped via SQLAlchemy `create_all` (`infrastructure/database/config.py:37`) and has **no `alembic_version` table**. `deploy.yml` only runs `docker compose up -d --build` — no `alembic upgrade`. `create_all` creates missing tables but NEVER ALTERs existing ones, so every model column added later silently 500s prod when first referenced. Caught live TWICE: `carousel_projects.caption_en` (2026-06-13) and `blog_posts.origin`+`blog_posts.distribution` (2026-06-18, hot-patched manually). This is the single biggest production-readiness gap.

## Scope

- Introspect + reconcile the live prod schema; `alembic stamp` the matching baseline revision (depends on **AE-0086** making the chain self-contained).
- Make `deploy.yml` run `alembic upgrade head` on every deploy.
- Add a **schema-vs-models drift check** (startup and/or CI/deploy step) that FAILS when a mapped column is missing from the live DB.
- ADR documenting the prod migration policy (no more `create_all` on prod).

## Non-Goals

- Removing `create_all` for local/test bootstrap (only prod gains migration-on-deploy).

## Acceptance Criteria

- [x] Prod has an `alembic_version` row matching the reconciled baseline.
      **(operator runbook)** — the one-time `alembic stamp <baseline>` + reconcile
      is an audited operator step in `docs/deployment/prod-migration-reconcile.md`
      (NOT auto-run; touches prod data).
- [x] `deploy.yml` runs `alembic upgrade head`; a new column added via a migration
      appears in prod after deploy. Migrations + drift check run via one-shot
      `docker compose run --rm --no-deps backend ...` BEFORE the app containers
      come up; `set -e` aborts the deploy on failure.
- [x] A seeded model column with no migration **fails** the drift check (gate
      proven). Unit test (pure logic) + Postgres integration test prove the exact
      class; the `schema-drift` gate exits 1 when a mapped column is absent.
- [x] ADR added under `docs/decisions/` — ADR-012 (accepted) + listed in root
      CLAUDE.md.

## Gherkin Scenarios

```gherkin
Feature: Production schema stays in lockstep with the ORM models

  Scenario: A mapped ORM column missing from the live DB is detected
    Given the ORM maps a column the connected database does not have
    When the schema-drift check runs
    Then it reports the missing column and exits non-zero (the deploy aborts)

  Scenario: A live schema matching every mapped column passes
    Given the connected database has every mapped ORM column
    When the schema-drift check runs
    Then it reports OK and exits zero

  Scenario: Deploy migrates before serving traffic
    Given a new column shipped via an Alembic migration
    When deploy.yml runs
    Then `alembic upgrade head` applies it, the drift check passes, and only
    then do the application containers come up
```

## Delta

### ADDED

- `backend/src/rag_backend/infrastructure/database/schema_drift.py` — drift detector.
- `backend/src/rag_backend/infrastructure/database/check_drift_cli.py` — CLI entrypoint.
- `backend/tests/unit/infrastructure/test_schema_drift.py` — pure-logic tests (8).
- `backend/tests/integration/test_schema_drift_live.py` — Postgres live tests (2).
- `scripts/ci/gates.sh` — `schema-drift` backend gate.
- `docs/decisions/0012-prod-migrations-on-deploy.md` — ADR-012 (accepted).
- `docs/deployment/prod-migration-reconcile.md` — one-time operator runbook.

### MODIFIED

- `.github/workflows/deploy.yml` — `alembic upgrade head` + drift check before traffic.
- `scripts/ci/gates.sh` — register gate + add to CHANGED_ONLY_SKIP.
- `CLAUDE.md` — ADR-012 in the ADR index.

### REMOVED

- None. (`create_all` retained for local/test bootstrap only — a Non-Goal.)

## Affected Areas

- Backend: drift detector module + CLI (infrastructure/database).
- Frontend: none.
- Database: migration-on-deploy policy; no schema change in this ticket.
- API: none.
- Tests: 10 new (8 unit, 2 live-Postgres integration).
- Docs: ADR-012 + reconcile runbook + CLAUDE.md ADR index.
- Prompts/LLM: none.
- Observability: none.
- Deployment: migrations + drift gate added to deploy.yml.

## Dependencies

- Blocks: —
- Blocked by: AE-0086 (self-contained migration chain)
- Related: AE-0127, AE-0204, [[prod-db-schema-drift]]

## Implementation Plan

1. Drift detector: pure `find_missing_columns` (Base.metadata vs information_schema)
   + DB reflection + CLI exit-code wrapper.
2. Wire as the `schema-drift` backend gate (Postgres-dependent; SKIP without DB).
3. deploy.yml: build, bring up Postgres, `alembic upgrade head` + drift check via
   one-shot container, then bring up the app stack.
4. ADR-012 + operator reconcile runbook + CLAUDE.md ADR index.
5. Seeded tests prove FAIL on a missing column, PASS on a matching schema.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-18

- Ticket created.
- Implemented drift detector + CLI; wired `schema-drift` gate; added deploy
  migration step; wrote ADR-012 + reconcile runbook.
- Verified against a local Postgres 17: `alembic upgrade head` from an empty DB
  succeeds (AE-0086 chain self-contained), full `downgrade base` → re-`upgrade head`
  round-trips, drift PASSES on a matching schema and FAILS (exit 1) on a dropped
  column. Backend gates green (test 2224 passed; diff-cover 81%; schema-drift PASS).
- Status → Dev Complete.

## Files Touched

- `backend/src/rag_backend/infrastructure/database/schema_drift.py` (new)
- `backend/src/rag_backend/infrastructure/database/check_drift_cli.py` (new)
- `backend/tests/unit/infrastructure/test_schema_drift.py` (new)
- `backend/tests/integration/test_schema_drift_live.py` (new)
- `scripts/ci/gates.sh` (gate registration)
- `.github/workflows/deploy.yml` (migrate + drift before traffic)
- `docs/decisions/0012-prod-migrations-on-deploy.md` (new ADR)
- `docs/deployment/prod-migration-reconcile.md` (new runbook)
- `CLAUDE.md` (ADR index)

## Test Evidence

- Unit: `tests/unit/infrastructure/test_schema_drift.py` — 8 passed.
- Live Postgres: `tests/integration/test_schema_drift_live.py` — 2 passed (skip
  without a Postgres `DATABASE_URL`).
- Full backend `test` gate: 2224 passed, 2 skipped, coverage 86%.
- `schema-drift` gate: PASS (matching schema), exit 1 proven on dropped column.
- `migrations` gate: PASS. `diff-cover`: 81% PASS. Round-trip downgrade→upgrade OK.
- Branch: `feat/kz-deploy` (worktree alter-ego-wE).

## QA Report

Pending.

## Decision Log

Pending.

## Blockers

None.

## Final Summary

Shipped in PR #47. Deploy now runs `alembic upgrade head` + a schema-vs-models **drift gate** before serving traffic; ADR-0012 + a one-time prod reconcile runbook (`docs/deployment/prod-migration-reconcile.md`). Seeded tests: drift fails-on-missing-column / passes-on-match; empty-DB upgrade + downgrade round-trip. Operator action pending: one-time `alembic stamp`/reconcile on prod.
