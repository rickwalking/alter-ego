# AE-0578 — Insight columns reach prod with the deploy, and the deploy checks schema drift

Status: In Development
Tier: T1
Priority: High
Type: Bug
Area: Backend
Owner: Pedro
Agent Lane: developer → qa → release
Branch: fix/ae-0578-ig-insight-columns-on-deploy
Kanban Card: TBD
Created: 2026-10-31
Updated: 2026-10-31

## Goal

The four insight columns of migration `f9a0b1c2d3e4` reach prod with every deploy, and a mapped ORM column that
is missing on prod fails the deploy job instead of 500ing the first read.

## Problem

`GET /api/autopilot/ig-insights` returned HTTP 500 "Database Error" on prod (2026-10-31, reported by the Grok
bot twice). Prod does not run Alembic on deploy (disabled since the 2026-06-18 outage) and bootstraps with
`create_all`, which created the new `ig_media` and `boost_requests` tables but never adds a column to an existing
table. So `instagram_post_insights` had no `likes`, `comments`, `avg_watch_time_ms` or `total_watch_time_ms`.
The `schema-drift` gate exists (`check_drift_cli`), but only CI runs it, against a database built by the
migrations, so it passed. Nothing was requested, approved or spent.

Prod was fixed by hand on 2026-10-31 (~11:40Z, Pedro's go): four
`ALTER TABLE instagram_post_insights ADD COLUMN IF NOT EXISTS <col> integer` in one transaction; the endpoint
answers 200, and a read-only drift sweep over every ORM base found nothing else missing.

## Scope

- An idempotent one-shot `python -m rag_backend.scripts.ig_insight_columns --apply --verify` (same shape as
  `carousel_archived_at`): adds the four nullable integer columns to an existing table, leaves a database without
  the table alone, no-op outside Postgres.
- `deploy.yml` runs it after the generation queue schema step, before the stack comes up. Once the stack is up
  (so the app's `create_all` has made any new table), it runs the read-only `check_drift_cli` in the running
  backend, retried up to 12 times while the backend starts. Both exits are captured and the job fails at the end;
  neither keeps prod down.

## Non-Goals

- Re-enabling `alembic upgrade` on deploy (needs the one-time prod stamp, `docs/deployment/prod-migration-reconcile.md`).
- Passing the four `META_*` ads variables through (pending Pedro).
- Any change to the insights API or its data.

## Acceptance Criteria

- [ ] AC1 Given a Postgres `instagram_post_insights` without the four columns, When the one-shot runs with
  `--apply --verify`, Then the columns exist as nullable integers, existing rows keep their data, exit 0.
- [ ] AC2 A second `--apply` adds nothing; `--verify` alone exits 1 and names the missing columns.
- [ ] AC3 A database without the table, or not Postgres, is left alone and exits 0; no mode is a usage error (2).
- [ ] AC4 Every column the one-shot adds is a nullable integer the ORM model maps.
- [ ] AC5 The deploy runs the one-shot (throwaway container) after the queue schema step and before stack up,
  and the drift check in the running backend after stack up, with retries; a failure of either is captured, the
  stack stays up, and the job fails at the end.

## Gherkin Scenarios

- `backend/tests/features/ig_insight_columns_oneshot_ae0578.feature`

## Repro Steps

1. Prod `instagram_post_insights` without the four columns (create_all bootstrap).
2. `GET /api/autopilot/ig-insights` with the scout key → 500 "Database Error".

## Affected Areas

- [x] Backend
- [ ] Frontend
- [x] Tests
- [x] Deploy workflow

## Dependencies

None.

## Progress Log

### 2026-10-31 11:40

Cause confirmed on prod (information_schema), columns added by hand, endpoint verified 200, drift sweep clean.

### 2026-10-31 11:45

One-shot, deploy wiring and tests written. Review: the drift check moved after stack up (before it, a new ORM
table that create_all makes at app start would read as drift), `lock_timeout` added to the one-shot, the
SQLite-only apply test replaced by a Postgres one. The deploy test fails on the old `deploy.yml` (6 failed).

## Files Touched

- `backend/src/rag_backend/infrastructure/database/ig_insight_columns.py`
- `backend/src/rag_backend/scripts/ig_insight_columns.py`
- `.github/workflows/deploy.yml`
- `backend/tests/features/ig_insight_columns_oneshot_ae0578.feature`
- `backend/tests/unit/scripts/test_ig_insight_columns_ae0578.py`
- `backend/tests/unit/scripts_ci/test_deploy_ig_insight_columns_ae0578.py`
- `backend/tests/integration/test_ig_insight_columns_ae0578.py`

## Test Evidence

Pending.

## QA Report

Pending.

## Blockers

None.
