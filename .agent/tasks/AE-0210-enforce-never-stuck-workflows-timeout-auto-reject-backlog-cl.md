# AE-0210 — Enforce never-stuck workflows: timeout auto-reject + backlog cleanup

Status: Intake
Tier: T2
Priority: High
Type: Bug
Area: backend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-18
Updated: 2026-06-18

## Goal

Stuck workflows are auto-rejected after a timeout (per CLAUDE.md), not left pending forever.

Source: Kaizen prod sweep `.agent/reports/kaizen-prod-2026-06-18.plan.md` (live carousel run, project b5b61790-9372-4a5a-ae17-30d2df28ef3d), validated by an independent architect cold-critic review.

## Problem

CLAUDE.md mandates "Auto-reject after timeout; never leave workflows stuck." But `application/workers/workflow_workers.py` + `WorkflowFailureAlertService` only emit `stuck_workflow` **warnings** — no transition. Prod has **14 workflows stuck at `brief/pending` since 2026-04-28** (verified live).

## Scope

- Implement timeout → auto-reject/cancel (configurable threshold) in the workflow worker.
- One-time cleanup of the existing stuck backlog (transition to a terminal state).
- Metric/alert on the stuck count.
- Seeded test: a workflow past the timeout is auto-transitioned.

## Non-Goals

- Changing the human-approval timeout for active reviews (separate policy).

## Acceptance Criteria

- [ ] A past-timeout workflow is auto-rejected/cancelled (no longer `pending`).
- [ ] The existing 14+ stuck workflows are cleaned up.
- [ ] Seeded timeout test passes.

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
- Related: AE-0017

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
