# AE-0396 — Telegram thesis edit reply is dropped (pending lookup ignores awaiting_thesis runs)

Status: In Development
Tier: T1
Priority: P0
Type: Bug
Area: backend
Owner: Claude (owner-reported hotfix)
Agent Lane: developer → qa → release
Branch: fix/ae-0396-thesis-edit-reply
Kanban Card: TBD
Created: 2026-10-16
Updated: 2026-10-16

## Goal

The owner's edited POV thesis, typed after "✏️ Editar" on Telegram, reaches the run.

## Problem

Prod 2026-10-16 (run b241ded5): the owner tapped Editar and typed a new thesis, and nothing happened. "Editar" stores the pending reply on the run, which is `awaiting_thesis`. `SqlPendingReworkStore.take` only scanned runs `awaiting_owner` (final review), so the typed thesis never matched and was dropped silently.

## Scope

- `take` scans `awaiting_owner` and `awaiting_thesis` runs.
- A pending reply only counts on a run in its own state: a thesis edit on `awaiting_thesis`, a rework on `awaiting_owner`. This keeps the existing guarantee that a stale text cannot undo an approve or reject.

## Non-Goals

- Changing the Telegram prompts or the thesis rules.

## Acceptance Criteria

- [x] AC1: A thesis typed after "Editar" is taken for the run awaiting its thesis.
- [x] AC2: A pending rework on an `awaiting_thesis` run, or a thesis edit on an `awaiting_owner` run, is ignored.
- [x] AC3: The existing rework round trip is unchanged.

## Gherkin Scenarios

```gherkin
Feature: Owner replies on Telegram reach their run (AE-0396)

  Scenario: An edited POV thesis typed after "Editar" is received
    Given a POV run awaiting its thesis with a pending "pov_thesis" reply
    When the owner sends the thesis text
    Then the reply is taken for that run

  Scenario: A pending reply only counts on a run in its own state
    Given a pending reply whose kind does not match the run's state
    When the owner sends text
    Then no run takes it
```

## Delta

### ADDED

- Integration tests in `test_autopilot_owner_actions.py` (thesis reply; state mismatch ×2)

### MODIFIED

- `modules/autopilot/infrastructure/pending_rework.py`

### REMOVED

- None.

## Affected Areas

- Backend: autopilot Telegram owner actions
- Frontend: none
- Database: none
- API: none
- Tests: integration
- Docs: this ticket
- Prompts/LLM: none
- Observability: none
- Deployment: none

## Dependencies

- Blocks: none
- Blocked by: none
- Related: AE-0377 (thesis gate)

## Implementation Plan

1. Scan both states in `take`; match the pending kind to the run state.
2. Integration tests.

## QA Checklist

- [x] Security reviewed (owner chat id still required; the state guard is kept)
- [x] Code quality reviewed
- [x] Acceptance criteria validated
- [x] Edge cases tested (mismatched kind/state)
- [x] Orphan/unfinished code checked

## Progress Log

### 2026-10-16 09:10

Reproduced from prod logs and the run's notice ledger; fixed. The owner's thesis for b241ded5 was confirmed by hand.

## Files Touched

See Delta.

## Test Evidence

- `test_autopilot_owner_actions.py`: 13 passed on Postgres.

## QA Report

Pending (hotfix fast path: CI Test & Coverage decides).

## Decision Log

- 2026-10-16: Match the pending kind to the run state instead of scanning all states, so stale texts stay harmless.

## Blockers

None.

## Final Summary

Pending.
