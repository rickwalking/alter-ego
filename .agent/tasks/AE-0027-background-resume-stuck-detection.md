# AE-0027 — Harden Background Resume Runner Against Silent Success

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

Harden `_execute_background_resume` so that when an `approve` resume completes but the workflow is still at the same phase (corrupted checkpoint), the system detects and reports this instead of silently "succeeding".

## Problem

When the `resume_workflow` call completes without exception but the workflow re-interrupts at the same gate (because `ainvoke(None)` re-ran the node and it `interrupt()`-ed again), the background task considers this a success. No error is logged, no SSE event is sent, and the project stays stuck at `research/awaiting_human` with no signal to the user.

The architect review confirmed: "the background task often 'succeeds' silently rather than failing loudly."

**Important**: `revise` and `reject` actions legitimately return to the same phase with `awaiting_human` — stuck detection must be scoped to `approve` only.

## Scope

- Add post-resume validation in `_execute_background_resume`: for `approve` actions only, compare `current_phase` before and after — if same phase and still `awaiting_human`, treat as a failed resume
- Log structured `background_resume_stuck` warning
- Publish error SSE event when resume doesn't advance
- Revert DB `phase_status` from `in_progress` back to `awaiting_human` on stuck detection

## Non-Goals

- Fixing the root cause (that's AE-0025)
- Changing the 202/fire-and-forget pattern
- Adding retry logic for background resume
- Detecting stuck for `revise` or `reject` actions (they legitimately return same phase)

## Acceptance Criteria

- [ ] WHEN background resume completes with action=approve but workflow is at same phase with awaiting_human THE SYSTEM SHALL log a `background_resume_stuck` warning
- [ ] WHEN background resume completes with action=approve but workflow is at same phase with awaiting_human THE SYSTEM SHALL publish an error SSE event
- [ ] WHEN background resume completes with action=approve but workflow is at same phase THE SYSTEM SHALL revert DB phase_status from "in_progress" to "awaiting_human"
- [ ] WHEN background resume completes with action=revise and workflow returns to same phase THE SYSTEM SHALL NOT log background_resume_stuck
- [ ] WHEN background resume completes with action=reject and workflow returns to same phase THE SYSTEM SHALL NOT log background_resume_stuck
- [ ] WHEN background resume completes and phase advances THE SYSTEM SHALL publish success SSE event (existing behavior)
- [ ] WHEN background resume throws ValueError THE SYSTEM SHALL mark phase as "failed" and publish error SSE (existing behavior, verified)

## Gherkin Scenarios

```gherkin
Feature: Background resume stuck detection

  Scenario: Approve resume completes but phase unchanged
    Given a carousel workflow is at research/awaiting_human
    And background resume executes with action=approve
    When the workflow returns research/awaiting_human
    Then a background_resume_stuck warning SHALL be logged
    And an error SSE event SHALL be published
    And DB phase_status SHALL be reverted to "awaiting_human"

  Scenario: Revise at same phase does not trigger stuck detection
    Given a carousel workflow is at research/awaiting_human
    And background resume executes with action=revise
    When the workflow returns research/awaiting_human
    Then no background_resume_stuck warning SHALL be logged
    And success SSE updates SHALL be published

  Scenario: Approve resume completes and phase advances
    Given a carousel workflow is at research/awaiting_human
    And background resume executes with action=approve
    When the workflow returns outline/awaiting_human
    Then success SSE updates SHALL be published
    And phase_status SHALL be updated in DB

  Scenario: Resume fails with ValueError
    Given a carousel workflow is at research/awaiting_human
    When background resume throws ValueError(ERR_PERSONA_SCORE_TOO_LOW)
    Then phase_status SHALL be set to "failed"
    And an error SSE event SHALL be published
```

## Delta

### MODIFIED

- `backend/src/rag_backend/application/services/carousel/editorial_workflow_resume_runner.py` — add post-resume stuck detection scoped to approve action

### ADDED

- Constant `ERR_BACKGROUND_RESUME_STUCK` in `carousel_workflow.py`
- Unit tests for stuck detection with approve/revise/reject action filtering

## Dependencies

- Depends on: AE-0025 (root cause must be fixed first, this is defense-in-depth)
- Related: AE-0026, AE-0017

## Implementation Plan

1. After `service.resume_workflow()` in `_execute_background_resume`, compare the returned state's `current_phase` with the pre-resume phase.
2. If `params.action == "approve"` AND same phase AND `phase_status=="awaiting_human"`, log warning and publish error SSE.
3. Revert DB `phase_status` from `"in_progress"` to `"awaiting_human"` using `_mark_background_resume_failed` or a new helper.
4. Add `ERR_BACKGROUND_RESUME_STUCK` constant.
5. Add unit tests with action filtering (approve triggers detection, revise/reject do not).

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested (approve stuck, revise same-phase, reject same-phase)

## Progress Log

### 2026-06-08

- Ticket created from architect review finding
- Updated with architect validation: scoped to `approve` action only, added DB revert, added revise/reject negative scenarios

## Files Touched

- `backend/src/rag_backend/application/services/carousel/editorial_workflow_resume_runner.py`
- `backend/src/rag_backend/domain/constants/carousel_workflow.py`

## Test Evidence

Pending.

## QA Report

See `.agent/reports/AE-0025-AE-0026-AE-0027.qa.md`.

## Decision Log

- Detection is defense-in-depth; primary fix is AE-0025
- Stuck detection scoped to approve action only (revise/reject legitimately return same phase)
- DB phase_status reverted from "in_progress" to "awaiting_human" on stuck detection to unblock future resumes

## Blockers

AE-0025 should be fixed first.

## Final Summary

Pending.