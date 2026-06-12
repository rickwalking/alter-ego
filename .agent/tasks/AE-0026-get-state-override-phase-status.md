# AE-0026 — Fix get_state() Overrides In-Progress Phase Status

Status: Review
Tier: T1
Priority: High
Type: Bugfix
Area: Backend/LangGraph
Owner: Unassigned
Agent Lane: developer -> qa -> release
Branch: fix/workflow-resume-interrupt-corruption
Kanban Card: TBD
Created: 2026-06-08
Updated: 2026-06-08

## Goal

Fix `CarouselWorkflowEngine.get_state()` to not mask `"in_progress"` phase status, and ensure `GET /workflow/state` returns `"in_progress"` during the resume window by merging DB `phase_status` when checkpoint and DB disagree.

## Problem

After AE-0025 removes checkpoint patching from `mark_resume_in_progress`:
- **DB** → `in_progress`
- **Checkpoint** → `awaiting_human` (interrupt preserved, as intended)
- **`get_state()`** reads checkpoint only → overrides `in_progress` to `awaiting_human`
- **`GET /workflow/state`** returns `awaiting_human` even during active background resume

This makes it impossible for:
- The frontend to show a "Processing approval..." spinner
- The `stuck_workflow` alert to distinguish between "stuck" and "actively resuming"
- SSE subscribers polling state to know the phase is being processed

This makes it impossible for:
- The frontend to show a "Processing approval..." spinner
- The `stuck_workflow` alert to distinguish between "stuck" and "actively resuming"
- SSE subscribers to know the phase is being processed

## Scope

- Fix `CarouselWorkflowEngine.get_state()` to not override `phase_status` when checkpoint already has `"in_progress"`, `"failed"`, or `"approved"`
- Merge DB `phase_status` into `get_workflow_state()` / `build_workflow_state_response()` when DB says `in_progress` but checkpoint says `awaiting_human` with pending interrupt
- Exclude `PHASE_STATUS_IN_PROGRESS` from stuck_workflow alert detection
- Update `test_alerts_on_stuck_workflow` integration test

## Non-Goals

- Fixing the root cause (that's AE-0025)
- Changing the 202 response format
- Adding new SSE event types

## Acceptance Criteria

- [ ] WHEN checkpoint phase_status is "in_progress" THE get_state() SHALL return "in_progress"
- [ ] WHEN checkpoint phase_status is "awaiting_human" AND DB project.phase_status is "in_progress" THE GET /workflow/state SHALL return "in_progress"
- [ ] WHEN checkpoint phase_status is "awaiting_human" AND DB project.phase_status is "awaiting_human" THE GET /workflow/state SHALL return "awaiting_human"
- [ ] WHEN checkpoint phase_status is "failed" THE get_state() SHALL return "failed" (not override to awaiting_human)
- [ ] WHEN checkpoint phase_status is "approved" THE get_state() SHALL return "approved" (not override to awaiting_human)
- [ ] WHEN a project has phase_status "in_progress" THE stuck_workflow alert SHALL NOT include it

## Gherkin Scenarios

```gherkin
Feature: Phase status observability

  Scenario: In-progress status preserved on poll (checkpoint)
    Given a carousel workflow checkpoint has phase_status "in_progress"
    And pending interrupts exist for the research gate
    When get_state is called
    Then the returned phase_status SHALL be "in_progress"

  Scenario: In-progress status from DB merged for API polling
    Given a carousel workflow checkpoint has phase_status "awaiting_human"
    And the DB project row has phase_status "in_progress"
    And pending interrupts exist for the research gate
    When GET /workflow/state is called
    Then the response phase_status SHALL be "in_progress"

  Scenario: Awaiting-human status preserved when no override
    Given a carousel workflow checkpoint has phase_status "awaiting_human"
    And the DB project row has phase_status "awaiting_human"
    And pending interrupts exist
    When get_state is called
    Then the returned phase_status SHALL be "awaiting_human"

  Scenario: Stuck workflow alert skips in-progress
    Given a project has phase_status "in_progress"
    When the stuck workflow detection runs
    Then the project SHALL NOT appear in stuck_workflow alerts

  Scenario: Stale in-progress eventually alerts (after TTL)
    Given a project has phase_status "in_progress"
    And the project was updated more than 30 minutes ago
    When the stuck workflow detection runs
    Then the project SHALL appear in stuck_workflow alerts with hours_stuck metadata
```

## Delta

### MODIFIED

- `backend/src/rag_backend/agents/carousel_workflow_engine.py` — `get_state()` conditionally overrides phase_status; respects `in_progress`, `failed`, `approved`
- `backend/src/rag_backend/application/services/carousel/editorial_workflow_service.py` — `get_workflow_state()` merges DB `phase_status` when DB says `in_progress` and checkpoint says `awaiting_human`
- `backend/src/rag_backend/api/routes/carousels/editorial_workflow.py` — `build_workflow_state_response()` uses merged status
- `backend/src/rag_backend/application/services/workflow_failure_alert_service.py` — exclude `PHASE_STATUS_IN_PROGRESS` from stuck detection (with TTL override for stale resumes)
- `backend/tests/unit/application/test_workflow_failure_alert_service.py` — update `test_alerts_on_stuck_workflow`

### ADDED

- Unit tests for get_state phase_status priority with DB merge

## Dependencies

- Depends on: AE-0025 (checkpoint must not be corrupted; DB-only in_progress approach)
- Related: AE-0017

## Implementation Plan

1. In `get_state()`, check `state.get("phase_status")` before overriding: if value is one of `PHASE_STATUS_IN_PROGRESS`, `PHASE_STATUS_FAILED`, `PHASE_STATUS_APPROVED`, don't override to `AWAITING_HUMAN`.
2. In `get_workflow_state()`, after calling `get_state()`, check DB project `phase_status`: if DB says `"in_progress"` and checkpoint says `"awaiting_human"` with pending interrupt, return `"in_progress"`.
3. In `build_workflow_state_response()`, use the merged status from step 2.
4. In `workflow_failure_alert_service.py`, add `phase_status != PHASE_STATUS_IN_PROGRESS` to the stuck detection query, with a TTL override (e.g., `in_progress` older than 30 minutes should still alert).
5. Add unit tests for all status priority cases and DB merge scenarios.
6. Update `test_alerts_on_stuck_workflow` to expect `in_progress` projects excluded.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested

## Progress Log

### 2026-06-08

- Ticket created from root cause analysis of carousel f2231ece resume bug

## Files Touched

- `backend/src/rag_backend/agents/carousel_workflow_engine.py`
- Stuck workflow alert module (TBD)

## Test Evidence

Pending.

## QA Report

See `.agent/reports/AE-0025-AE-0026-AE-0027.qa.md`.

## Decision Log

- get_state should trust checkpoint phase_status over derived status when checkpoint explicitly says "in_progress", "failed", or "approved"
- DB merge is required because after AE-0025, checkpoint stays "awaiting_human" during the resume window while DB says "in_progress"
- Stuck alert excludes "in_progress" with TTL override for truly stale resumes

## Blockers

AE-0025 must be fixed first (otherwise checkpoint is corrupted and get_state fix is invisible).

## Final Summary

Pending.