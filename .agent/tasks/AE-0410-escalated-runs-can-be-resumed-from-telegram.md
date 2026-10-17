# AE-0410 — Escalated runs can be resumed from Telegram

Status: Intake
Tier: T2
Priority: High
Type: Feature
Area: Backend
Owner: Unassigned
Agent Lane: architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-10-17
Updated: 2026-10-17

## Goal

When an autopilot run escalates at a quality gate (content, design, images), the owner can fix it
and hand it back from Telegram (or by fixing it in the dashboard) without anyone editing the
database.

## Problem

Carousel `be190a0c` / run `f88bc343`, 2026-10-17: the run escalated twice at the content gate
(02:33Z and 04:04Z, `persona_score_below_threshold`). Both times the only way forward was an
orchestrator script: patch the checkpoint, then `UPDATE autopilot_runs SET state='generating'`
directly, bypassing the state machine.

What the code does today (from `origin/main`):

- `escalated` can only move to `awaiting_owner` or `rejected`
  (`modules/autopilot/domain/state_machine.py:21-53`). Nothing goes back to `generating`.
- The escalation Telegram notice has **no buttons**: `status_keyboard` returns None except for
  `publish_failed` / `review_reopened` (`modules/autopilot/domain/status_keyboard.py:25-33`). Owner
  callbacks require `awaiting_owner` (Retry requires `publish_failed`)
  (`application/owner_steps.py:34-71`, `owner_actions.py:276-282`).
- `RunRecovery.sweep` wakes an escalated run only at `final_review` / `awaiting_human` after the
  lock version changes (`application/run_recovery.py:99-104, 212-258, 286-304`). A run escalated at
  the **content** gate is never re-evaluated, even after the owner fixes the slides in the
  dashboard. After 72 h it is rejected.

## Scope

- The escalation notice gets buttons:
  - **🔁 Tentar de novo** (retry): moves the run back so the runner re-evaluates the same gate on
    the next tick (re-reads the checkpoint, runs the deterministic repair and the AE-0407 slide fix,
    then approves or escalates again). Counts as a gate attempt; capped (for example 2 retries per
    gate) so it can't loop.
  - **✏️ Corrigir no painel**: a deep link to the dashboard project page at the failing gate.
  - **❌ Descartar**: rejects the run (existing reject path).
- The escalation message names the failing slides and the rule codes (from the AE-0401 report).
- `RunRecovery.sweep` also wakes a run escalated at **content/design/images** when the owner edits
  the project (lock version changes, as it already does for final review): it re-evaluates the gate
  instead of waiting for the 72 h reject.
- New legal transition `escalated → generating` (reason `owner_retry` / `owner_fixed`), done
  through the repository's compare-and-set, never raw SQL.

## Non-Goals

- Changing why gates fail (AE-0407, AE-0409).
- Final-review behavior (already handled by `awaiting_owner`).

## Acceptance Criteria

- [ ] An escalation notice at a quality gate shows Retry, Fix in dashboard and Discard buttons.
- [ ] Retry moves `escalated → generating` through the state machine; the next tick re-evaluates
      the same gate and approves when it now passes.
- [ ] Retry is capped per gate; past the cap the button explains why and only Fix/Discard remain.
- [ ] An owner edit in the dashboard of a run escalated at content/design/images wakes the run
      (lock version change) and re-evaluates the gate.
- [ ] The escalation message lists the failing slides and rule codes.
- [ ] Callbacks are owner-only and idempotent (a double tap does one transition).
- [ ] No raw SQL is needed to resume an escalated run (documented runbook updated).

## Gherkin Scenarios

```gherkin
Feature: Resume an escalated autopilot run

  Scenario: Retry after the content gate escalates
    Given an autopilot run escalated at the content gate
    When the owner taps "Tentar de novo" on the escalation message
    Then the run moves to generating
    And the next tick re-evaluates the content gate

  Scenario: The owner fixes the slides in the dashboard
    Given an autopilot run escalated at the content gate
    When the owner saves manual fixes for that project in the dashboard
    Then the run wakes and the content gate is re-evaluated

  Scenario: Retries are capped
    Given an autopilot run that already used its retries at the content gate
    When the owner taps "Tentar de novo"
    Then the run stays escalated
    And the owner is told to fix it in the dashboard or discard it

  Scenario: Discard from the escalation message
    Given an autopilot run escalated at the design gate
    When the owner taps "Descartar"
    Then the run is rejected and nothing is published

  Scenario: A double tap does one transition
    Given an autopilot run escalated at the content gate
    When the owner taps "Tentar de novo" twice
    Then the run moves to generating exactly once
```

## Delta

### ADDED

- Escalation keyboard (retry, fix link, discard) and callbacks.
- `escalated → generating` transition with a per-gate retry cap.
- Sweep wake for runs escalated at content/design/images.

### MODIFIED

- `state_machine.py`, `status_keyboard.py`, `owner_steps.py` / `owner_actions.py`,
  `run_recovery.py`, the escalation message text.

### REMOVED

- None.

## Affected Areas

- Backend: autopilot state machine, Telegram keyboards/callbacks, run recovery.
- Frontend: none (deep link only).
- Database: a per-gate retry counter on `autopilot_runs` if needed (migration: prod applies SQL by
  hand, see ADR-012 / AE-0207 notes; add the column on prod before merging).
- API: Telegram webhook callbacks only.
- Tests: Gherkin above, state machine transitions, callback idempotency.
- Docs: `docs/architecture/grokbot-autopilot.md` (escalation and recovery).
- Prompts/LLM: none.
- Observability: log retries and wakes with the gate and reason.
- Deployment: possible manual column add on prod.

## Dependencies

- Blocks: none.
- Blocked by: none.
- Related: AE-0401 (autofix escalation report), AE-0407, AE-0409.

## Implementation Plan

1. Architect: confirm the retry semantics with the runner's `_tick_active` and the sweep, and the
   cap storage.
2. State machine + repository transition, then callbacks and keyboard.
3. Sweep wake for quality-gate escalations.
4. Escalation message content (slides + rules).

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-10-17 05:00

Ticket created from the `be190a0c` incident (two content-gate escalations resumed by raw SQL).

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
