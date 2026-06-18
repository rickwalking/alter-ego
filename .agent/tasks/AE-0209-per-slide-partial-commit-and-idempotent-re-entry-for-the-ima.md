# AE-0209 — Per-slide partial-commit and idempotent re-entry for the images phase

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

A single slide's image failure must not discard the whole images phase; successful images persist and the phase is re-entrant.

Source: Kaizen prod sweep `.agent/reports/kaizen-prod-2026-06-18.plan.md` (live carousel run, project b5b61790-9372-4a5a-ae17-30d2df28ef3d), validated by an independent architect cold-critic review.

## Problem

`nodes/images.py:521` uses `asyncio.gather`, so one slide's exception aborts the whole batch; successful images are never committed to workflow state (prod b5b61790: `image_assets`=0 despite 5 JPGs on disk). Generation is already idempotent (`prompt_hash`). **Correction (cold-critic):** the stale-`in_progress`-lock claim is FALSE — `editorial_workflow_resume_runner._mark_background_resume_failed` already sets `phase_status='failed'` (lock-release shipped via AE-0027). The real gap is partial-commit + idempotent re-entry. (Secondary: verify the failure/cancellation path always runs so a killed background task can't leave a half state.)

## Scope

- Commit per-slide image successes incrementally (don't gate on the whole batch).
- Make the images phase re-entrant: on resume, skip already-generated (cached by `prompt_hash`) and generate only the missing.
- Verify the background-resume failure AND cancellation paths always release the lock.
- Seeded test: inject a single-slide failure → other slides persist, a retry completes the phase.

## Non-Goals

- Re-architecting the checkpointer (see AE-0213).

## Acceptance Criteria

- [ ] Partial image successes are persisted to workflow state on a mid-batch failure.
- [ ] Re-running the images phase regenerates only missing slides and completes.
- [ ] Seeded single-slide-failure test passes.

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
- Related (extends): AE-0017; AE-0027 (resume failure handling)

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
