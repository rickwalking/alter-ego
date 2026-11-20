# AE-0631 — Deploy one-shot for the reel cover columns (prod schema drift after AE-0627)

Status: In Development
Tier: T1
Priority: Critical
Type: Bug
Area: Backend
Owner: Pedro
Agent Lane: developer → qa → release
Branch: fix/ae-0631-reel-cover-columns-oneshot
Kanban Card: TBD
Created: 2026-11-20
Updated: 2026-11-20

## Goal

Get the reel cover columns of AE-0627 to prod through the deploy, so the cover table matches the ORM on every deploy,
including a rebuilt database.

## Problem

PR #370 (AE-0626..0629) added `purpose` and `repost_id` to the existing `autopilot_cover_assets` table in migration
`c3d4e5f6a7b9`. Prod does not run Alembic on deploy: `create_all` made the two new repost tables but never adds a
column to an existing table, and no one-shot was shipped. The 2026-11-20 deploy of 824c5686d failed its schema drift
check (`autopilot_cover_assets.purpose`, `autopilot_cover_assets.repost_id` absent). From 20:56 to about 21:01 UTC
every read of a cover asset failed; the `telegram_notices` worker step logged a failure each minute.

Mitigated by hand at about 21:01 UTC: the migration's two `ADD COLUMN IF NOT EXISTS` statements were run on prod, and
the drift check then reported "live schema matches all mapped ORM columns". This ticket makes the fix part of the
deploy.

## Scope

- `infrastructure/database/reel_cover_columns.py`: idempotent apply/verify for `purpose VARCHAR(16) NOT NULL DEFAULT
  'carousel_cover'` and `repost_id UUID NULL`. Short lock timeout, no-op without the table or outside Postgres.
- `scripts/reel_cover_columns.py`: the `--apply` / `--verify` CLI.
- `deploy.yml`: run it after the token version one-shot and before the stack comes up. Capture its exit; fail the job
  at the end with the stack up.

## Non-Goals

- No in-stack retry: unlike the users columns, a missing cover column does not break sign-in.
- No change to the migration, the ORM model or app code.

## Acceptance Criteria

- [x] AC1 On a cover table without the columns, `--apply --verify` adds `purpose` (NOT NULL varchar, existing rows
  read `carousel_cover`) and `repost_id` (nullable uuid), keeps the rows, and exits 0.
- [x] AC2 A second run adds nothing; `--verify` alone exits 1 and names the missing columns.
- [x] AC3 A database without the table, or one that is not Postgres, is left alone and exits 0.
- [x] AC4 The one-shot's columns match the ORM model (type, nullability, default); the CLI needs a mode.
- [x] AC5 The deploy runs it after the token version step and before stack up; a failure keeps the stack up and fails
  the job at the end.
- [ ] AC6 The next deploy's drift check passes; every PR workflow is green except mutation (hotfix fast path).

## Gherkin

`backend/tests/features/reel_cover_columns_oneshot_ae0631.feature`

## Affected Areas

- `backend/src/rag_backend/infrastructure/database/reel_cover_columns.py`
- `backend/src/rag_backend/scripts/reel_cover_columns.py`
- `.github/workflows/deploy.yml` (apparatus edit: one new one-shot step and its final check, same shape as the
  `ig_insight_columns` step)

## Dependencies

- Follows AE-0627 (PR #370).

## Progress Log

- 2026-11-20: prod mitigated by hand (DDL identical to the migration; drift check OK; worker step healthy from the
  21:01:28 tick). One-shot, deploy step and tests written.

## Files Touched

- `.github/workflows/deploy.yml`
- `backend/src/rag_backend/infrastructure/database/reel_cover_columns.py`
- `backend/src/rag_backend/scripts/reel_cover_columns.py`
- `backend/tests/features/reel_cover_columns_oneshot_ae0631.feature`
- `backend/tests/unit/scripts/test_reel_cover_columns_ae0631.py`
- `backend/tests/unit/scripts_ci/test_deploy_reel_cover_columns_ae0631.py`
- `backend/tests/integration/test_reel_cover_columns_pg_ae0631.py`

## Test Evidence

- Unit and deploy-order tests: 25 passed, including the existing token version, insight columns and drain-worker
  deploy tests.
- Postgres 16 integration: 4 passed.
- Single gates on the branch (hotfix fast path, mutation in CI): format, lint, lint-diff, blanket-ignore, strict-diff,
  type, imports, arch-ratchet, docstrings, dead-code, inline-prompts, gherkin-refs, comments, blog-v1-dead-code,
  redis-factory, autopilot-env, healthcheck-loopback, openapi-fresh, bandit, pip-audit, integrity, duplication,
  migrations, schema-drift: PASS. Local Python is 3.11, matching the prod image.

## Decision Log

- 2026-11-20: Same pattern as `ig_insight_columns` (AE-0578). The deploy's drift check caught the gap, as designed.
  The AE-0627 review missed that a new column on an existing table needs a deploy one-shot.
