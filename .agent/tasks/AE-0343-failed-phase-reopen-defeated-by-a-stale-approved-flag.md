# AE-0343 — a stale approved flag defeats the failed-phase reopen (silent no-op retry survives)

Status: Ready
Tier: T2
Priority: High
Type: Bug
Area: Backend
Owner: Unassigned
Agent Lane: developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-09-15
Updated: 2026-09-15

## Goal

Close the last path by which a retry after a failed phase is a silent no-op.
A run that ended on `phase_status=failed` must always re-enter that phase on
retry, regardless of what the phase's approved flag happens to say.

## Problem

Found by external QA on the merged AE-0330 work (2026-09-15). AE-0330 made a
failed phase route to `END` instead of self-looping, and taught
`needs_gate_reopen` to re-enter a phase that ended at `failed`. But
`needs_gate_reopen` still applies its **approved-field guard**, and there is a
live sequence in which that flag is stale-True while the phase has failed:

1. A send-back from **final review** (or the approved-hold node) to `content`
   does **not** reset `content_approved`. Only the design node resets it.
2. The content regeneration then fails. The early-return path returns the merged
   state to `END` carrying **both** `content_approved=True` and
   `phase_status=failed`.
3. On retry, `needs_gate_reopen` sees the approved flag set, evaluates to
   `False`, and the service issues a plain `Command(resume)` against a graph that
   has already finished — **the exact silent no-op AE-0330 set out to remove**.
   Nothing at the service layer catches it; the carousel is stuck.

Arguably the approved-field guard should not apply at all when
`phase_status == failed`: a failed phase has no meaningful approval.

The existing regression test
(`test_failed_phase_at_end_is_reopened_on_retry`) only exercises
`content_approved=False`, so this path is untested.

## Scope

- `needs_gate_reopen`: when `phase_status == failed`, reopen the phase without
  consulting the approved flag.
- Alternatively/additionally: clear the target phase's approved flag on every
  send-back that targets it (the design node already does this for content —
  make it uniform), so a stale flag cannot reach a failed return.
- Decide between the two (or apply both) and record the reasoning; prefer the
  `needs_gate_reopen` fix as the load-bearing one since it is closest to the
  failure.
- Extend the test matrix so both flag values are covered for a failed phase.
- **Test-coverage gap from the same review:** `test_every_gated_phase_maps_failed_to_end`
  enumerates only 4 of the 6 gated phases (images is wired but unasserted).
  Cover all gated phases, and correct the Gherkin in
  `carousel_failed_phase_terminates.feature`, which claims the failed edge is
  wired on *every* gated phase — `route_after_final_review` has no failed branch
  (safely, since it can never return one, but the scenario text is untrue).
- `GraphRecursionError` has no handler anywhere in `backend/src`: on resume it is
  swallowed by a broad `except Exception`, on `workflow/start` it escapes as a
  raw 500. Give it a typed handler and an explicit log/alert.

## Non-Goals

- Re-litigating the failed → END routing itself (AE-0330 got it right).
- Changing the send-back UX.
- The `phase_feedback` lifetime problem (AE-0335).

## Acceptance Criteria

- [ ] A run that ends at `phase_status=failed` with `content_approved=True`
      re-enters the content phase on retry — regression test drives exactly the
      final-review → content → fail → retry sequence.
- [ ] The same holds with `content_approved=False` (existing behaviour preserved).
- [ ] `test_every_gated_phase_maps_failed_to_end` asserts all gated phases.
- [ ] The Gherkin scenario text matches what is actually wired.
- [ ] `GraphRecursionError` is caught with a typed handler, logged distinctly,
      and surfaced as a meaningful failure rather than a raw 500.
- [ ] `bash scripts/ci/gate-capture.sh backend` green; GATES_JSON in the dev summary.

## Gherkin Scenarios

```gherkin
Feature: A failed phase always reopens on retry

  Scenario: Retry after a failure that carried a stale approved flag
    Given the reviewer sent the carousel back from final review to content
    And the content phase then failed
    And the content approved flag is still set from the earlier cycle
    When the run is retried
    Then the content phase is re-entered
    And the retry is not a no-op

  Scenario: Retry after a failure with no approval
    Given the content phase failed and is not approved
    When the run is retried
    Then the content phase is re-entered

  Scenario: A runaway loop is reported, not swallowed
    Given the graph exceeds its recursion limit
    When the error propagates
    Then it is caught by a typed handler and logged as a loop
    And it is not returned as an unclassified 500
```

## Affected Areas

- Backend: `agents/carousel_workflow_graph.py` (`needs_gate_reopen`), `agents/carousel_workflow_nodes.py`, resume runner, `api/routes/carousels/editorial_workflow.py`
- Frontend: no
- Database: no
- API: error classification for a loop
- Tests: `tests/unit/agents/test_carousel_workflow_failed_phase.py`, `tests/features/carousel_failed_phase_terminates.feature`
- Docs: no
- Prompts/LLM: no
- Observability: distinct log/alert for a recursion-limit hit
- Deployment: no

## Dependencies

- Blocks: a fully reliable retry after a failed phase
- Blocked by: none
- Related: AE-0330 (the fix this completes), AE-0335, AE-0339

## Implementation Plan

1. Write the failing test for the final-review → content → fail → retry sequence.
2. Make `needs_gate_reopen` ignore the approved flag when `phase_status == failed`.
3. Audit send-backs so the target phase's approved flag is reset uniformly.
4. Extend the gated-phase mapping test to all phases; fix the Gherkin text.
5. Add the typed `GraphRecursionError` handler.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested (both flag values; send-back from approved-hold)
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-09-15

Created from the retroactive external QA of AE-0330 (see
`.agent/reports/AE-0330.qa.md`). Reported as MAJOR; not a regression introduced
by AE-0330, but the one path its fix does not cover.

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
