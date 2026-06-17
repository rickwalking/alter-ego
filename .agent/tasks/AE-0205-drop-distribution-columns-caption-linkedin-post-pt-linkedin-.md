# AE-0205 — Drop distribution columns caption/linkedin_post_pt/linkedin_post_en (destructive)

Status: Intake
Tier: T2
Priority: Medium
Type: Task
Area: backend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-17
Updated: 2026-06-17

## Goal

Drop the three distribution columns `caption`, `linkedin_post_pt`,
`linkedin_post_en` from `carousel_projects` once AE-0204 has given them a
canonical home and migrated every reader/writer. DESTRUCTIVE + consent-gated.

## Problem

These columns are the legacy embedded distribution copy on the shared
`carousel_projects` god-row (ADR-0009 single-writer violation). They cannot be
dropped until AE-0204 lands (canonical home + reader/writer migration + checkpoint
decoupling). The original AE-0162 conflated this with the blog-column drop and
falsely assumed AE-0163 had retired the writers — it had not.

## Scope

- Destructive Alembic migration: `op.drop_column` × 3 (downgrade re-adds them
  `nullable=True`; downgrade restores SCHEMA only, NOT data).
- Pre-drop `pg_dump` backup of the three columns (the rollback artifact).
- **Checkpoint drain**: confirm no live `AsyncPostgresSaver` checkpoint carries
  `caption`/`linkedin_post_pt`/`linkedin_post_en` state keys (resumed pre-drop
  checkpoints re-write dropped columns → `UndefinedColumn`).
- **Prod schema introspection** before running (prod is `create_all`-bootstrapped,
  has NO Alembic — do not trust the local chain).

## Non-Goals

- `blog_markdown`/`blog_translations` (blog slice — AE-0162).
- `caption_en` (write-dead — AE-0206).
- Building the canonical home (AE-0204).

## Acceptance Criteria

- [ ] Word-boundary grep: zero readers/writers of the three columns in
      `backend/src` (only the migration references them).
- [ ] `pg_dump` backup of the three columns captured and stored.
- [ ] Checkpoint drain verified (no live checkpoint carries the state keys).
- [ ] Prod `carousel_projects` schema introspected and matches the migration's
      expected pre-state.
- [ ] Migration drops the 3 columns; `downgrade` re-adds them `nullable=True`;
      fresh-DB upgrade→autogenerate-drift=0→downgrade→upgrade round-trips.
- [ ] AE-0125 safety net diff = 0.

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

- Blocks: (none)
- Blocked by: **AE-0204** (canonical home + reader/writer migration + checkpoint
  decoupling) AND an explicit human consent + drain window
- Related: AE-0162, AE-0133

## Implementation Plan

1. ...

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-17 HH:mm

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
