# AE-0213 — Durable LangGraph checkpointer in prod (postgres) + startup guard

Status: Intake
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

- [ ] Prod uses the postgres checkpointer; `checkpoint*` tables exist in prod DB.
- [ ] Startup guard rejects/warns on a non-durable backend outside dev.

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
