# AE-0207 — Reconcile prod DB to Alembic and run migrations on deploy

Status: Intake
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

- [ ] Prod has an `alembic_version` row matching the reconciled baseline.
- [ ] `deploy.yml` runs `alembic upgrade head`; a new column added via a migration appears in prod after deploy.
- [ ] A seeded model column with no migration **fails** the drift check (gate proven).
- [ ] ADR added under `docs/decisions/`.

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
- Blocked by: AE-0086 (self-contained migration chain)
- Related: AE-0127, AE-0204, [[prod-db-schema-drift]]

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

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Decision Log

Pending.

## Blockers

None.

## Final Summary

Pending.
