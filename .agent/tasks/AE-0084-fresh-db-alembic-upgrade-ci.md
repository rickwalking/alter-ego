# AE-0084 — Fresh-database `alembic upgrade head` CI job

Status: Ready
Tier: T2
Priority: Medium
Type: Task
Area: CI/DevOps
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0084-fresh-db-migration-ci
Kanban Card: TBD
Created: 2026-06-12
Updated: 2026-06-12

## Goal

Add a CI job that provisions a fresh database and runs `alembic upgrade head`, failing on any migration error — a guard that does not exist today.

## Problem

There is no CI check that the migration chain applies cleanly from scratch, so drift (a broken or out-of-order revision) can land undetected. Phase 1 adds this before any Phase 4+ schema work.

## Scope

- Add a job/step to the EXISTING backend CI workflow that spins a fresh Postgres service and runs `alembic upgrade head` (and optionally `downgrade base` round-trip) from an empty DB.
- Fail the job on any alembic error; pass when the chain applies cleanly.
- No new standalone workflow files if it fits the existing backend gates; no deployment CI changes.

## Non-Goals

- No changes to existing migrations' logic (fix-forward only if the job exposes a real break).
- No production deployment pipeline changes.

## Modularization Alignment (2026-06-12)

Phase 1 of the approved modularization plan (`.agent/reports/domain-modularization.options.md` §Phase 1). Scaffolding only — **no behavior moves, no schema changes, no route changes, no write redirection** (plan exit gate). The migrate-in-place delta review cleared Phase 1 (`.agent/reports/domain-modularization.delta-review.md`); the 4 residual WARNs are pre-Phase-4 (`docs/architecture/phase-0-risk-register.md`) and do not apply here. Use glossary (AE-0071) context names and ADR-0009 conventions. This is the plan's 'fresh-database alembic upgrade head migration job to CI' deliverable; it underpins the Phase 4+ migrate-in-place windows (reversible-path discipline).

## Acceptance Criteria

- [ ] WHEN backend CI runs THE pipeline SHALL run `alembic upgrade head` against a fresh database within a bounded timeout and fail if any migration errors or the step times out
- [ ] WHEN `alembic downgrade base` is run after `upgrade head` on the fresh DB THE round-trip SHALL succeed (catches non-reversible revisions early — supports Phase 4+ reversible-path discipline)
- [ ] WHEN the migration chain is clean THE job SHALL pass
- [ ] WHEN a deliberately broken revision is present THE job SHALL fail (demonstrated locally / in a scratch test)
- [ ] THE job SHALL live in the existing backend CI workflow (no deployment CI changes, minimal new workflow files)

## Gherkin Scenarios

```gherkin
Feature: Migrations apply from scratch

  Scenario: clean chain passes
    Given an empty database
    When CI runs alembic upgrade head
    Then all revisions apply and the job passes

  Scenario: broken revision fails CI
    Given a migration that errors on a fresh DB
    When CI runs alembic upgrade head
    Then the job fails
```

## Delta

### ADDED

- CI job/step: fresh-DB alembic upgrade head

### MODIFIED

- existing backend CI workflow (add migration job)

### REMOVED

- None

## Affected Areas

- Backend: none (CI only)
- Frontend: none
- Database: none (CI provisions ephemeral DB)
- API: none
- Tests: none
- Docs: gate note in qa-checkpoints
- Prompts/LLM: none
- Observability: none
- Deployment: no (gate only)

## Dependencies

- Blocks: none
- Blocked by: none
- Related: AE-0049

## Implementation Plan

1. Add a Postgres service + alembic upgrade head step to the backend workflow.
2. Confirm green on the current chain; verify a broken revision fails (scratch).
3. Document the gate in docs/guides/qa-checkpoints.md.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-12

Ticket created by planner (Phase 1 epic breakdown).

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
