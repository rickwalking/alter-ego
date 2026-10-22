# AE-0495 — Stop stuck_workflow alert spam

Status: Review
Tier: T1
Priority: Medium
Type: Bug
Area: Backend
Owner: Pedro Marins
Agent Lane: developer → qa → release
Branch: fix/ae-0495-stuck-workflow-alert-spam
Kanban Card: TBD
Created: 2026-10-22
Updated: 2026-10-22

## Goal

A stuck carousel project alerts the admins once per stuck episode, and the log stays quiet while nothing is new.

## Problem

Prod logs a `workflow_failure_alert` / `stuck_workflow` warning every minute for the same 15 projects, and each admin
gets the same notification again every hour. In `WorkflowFailureAlertService._alert_stuck_workflows` the warning is
logged before the dedupe check, so it fires on every minute-worker run; the dedupe only looks back
`ALERT_FAILURE_WINDOW_HOURS = 1`, so the notification is re-created hourly. The constant noise also hides real alerts
(and kept the high-failure-rate alert, which skips while any recent workflow-failure notification exists, suppressed).

## Scope

- A stuck episode starts at the project's `updated_at`; the stuck check alerts (log line + one notification per
  admin) only when no workflow-failure notification for that project exists since then.
- The log line moves after the dedupe check: one line per new alert, none for already-alerted projects.

## Non-Goals

- Archiving / closing stale projects (AE-0496).
- Failed-carousel and high-failure-rate checks (unchanged).

## Acceptance Criteria

- [x] Given a project stuck > 48 h, When the minute worker runs, Then one `stuck_workflow` log line and one
      notification per admin are emitted once per stuck episode (not every minute, not every hour).
- [x] Given the project changes phase/status and gets stuck again, Then it alerts again.
- [x] Given 15 stuck projects already alerted, Then a run emits no alert and no `stuck_workflow` log line.
- [x] Real alerts are kept: a newly stuck project and a stale in-progress run still alert; a stalled in-progress
      run alerts once per stall.
- [x] Only workflow-failure notifications mark an episode as alerted (a deadline reminder does not silence it).

## Gherkin Scenarios

```gherkin
Feature: Stuck workflow alerts fire once per stuck episode

  Scenario: A stuck project alerts once per stuck episode
    Given a carousel project not updated for more than 48 hours
    When the workflow worker checks the project on several runs, hours apart
    Then one stuck_workflow log line and one notification per admin are emitted on the first run
    And the later runs emit no log line and no notification

  Scenario: A project that moves and gets stuck again alerts again
    Given a stuck project whose admins were already alerted
    When the project changes phase and then stays unchanged for more than 48 hours
    Then the next run alerts the admins again for the new stuck episode

  Scenario: Already alerted stuck projects keep the log quiet
    Given 15 stuck projects whose admins were already alerted in this episode
    When the workflow worker runs
    Then no alert is emitted and no stuck_workflow log line is written
```

## Delta

### ADDED

- `_alerted_in_episode` (notification for the project since its `updated_at`).
- `backend/tests/features/stuck_workflow_alerts.feature` and three unit tests.

### MODIFIED

- `_alert_stuck_workflows`: dedupe per episode, log after the dedupe.

### REMOVED

- The 1-hour window for stuck alerts.

## Affected Areas

- Backend: workflow failure alert service.
- Frontend: none.
- Database: none (uses existing notification rows; no schema change).
- API: none.
- Tests: unit (SQLite).
- Docs: none.
- Prompts/LLM: none.
- Observability: `stuck_workflow` warnings drop from one per project per minute to one per episode.
- Deployment: none. Already-notified prod projects stay quiet after deploy (their notifications post-date the
  episode start).

## Dependencies

- Blocks: none.
- Blocked by: none.
- Related: AE-0496 (archive stale projects).

## Implementation Plan

1. Feature + failing tests (once per episode, re-alert after moving, quiet run for 15 alerted projects).
2. Episode dedupe; log after it.

## QA Checklist

- [x] Security reviewed
- [x] Code quality reviewed
- [x] Acceptance criteria validated
- [x] Edge cases tested
- [x] Orphan/unfinished code checked

## Progress Log

### 2026-10-22 18:00

Tests red (2); episode dedupe added; alert service and worker-notify tests green.

### 2026-10-22 19:20

External QA (WARN, suggestions only): added scenarios + tests for other notification types and for a stalled
in-progress run; the type-filter mutant is now killed (checked by removing the filter: the test fails).

## Files Touched

- backend/src/rag_backend/application/services/workflow_failure_alert_service.py
- backend/tests/unit/application/test_workflow_failure_alert_service.py
- backend/tests/features/stuck_workflow_alerts.feature (new)

## Test Evidence

See `.agent/reports/AE-0495.dev-summary.md`.

## QA Report

`.agent/reports/AE-0495.qa.md`.

## Decision Log

- No summary log line on a quiet run: one per minute would be its own spam; a run with nothing new logs nothing.
- The episode marker is the existing notification row, so no schema change and no deploy one-shot.

## Blockers

None.

## Final Summary

Pending.
