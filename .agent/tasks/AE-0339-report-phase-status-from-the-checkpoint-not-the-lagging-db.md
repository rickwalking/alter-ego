# AE-0339 — report phase status from the checkpoint, not the lagging DB label

Status: Ready
Tier: T2
Priority: Medium
Type: Bug
Area: Backend
Owner: Unassigned
Agent Lane: developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-09-15
Updated: 2026-09-15

## Goal

The status a human (or an alert) reads must match where the workflow actually is.
A run parked at an interrupt must not be reported as having completed that phase.

## Problem

The DB `phase_status` label **lags the checkpoint**. Observed on carousel
`dcaa5fef…`: the DB reported `images / approved` while the graph was in fact
parked at the **images `__interrupt__`** — waiting for human approval, not done
with it.

The practical damage is alert noise that hides real problems: the **18 "stuck at
approved" alerts** raised over this period are very plausibly all this same
mislabel rather than 18 stuck runs. The diagnostic that actually works is to look
for an `__interrupt__` entry in `checkpoint_writes` for the thread **before**
concluding anything is stuck — i.e. operators currently have to bypass the
product's own status field to learn the truth.

Related context worth carrying into the fix: the checkpoint thread id **is the
project id verbatim** (`carousel_workflow_engine.py:64` sets
`{"thread_id": project_id}`), so joining status to checkpoint state is cheap.

## Scope

- Derive the reported phase status from the checkpoint's actual position
  (including a pending `__interrupt__`) rather than from the standalone DB label —
  or write the DB label at the same moment the interrupt is raised so it cannot lag.
- Add an explicit `awaiting_approval` (or equivalent) state distinct from
  `approved`, so "parked at a gate" is representable instead of being rounded to
  the nearest completed phase.
- Update the stuck-run alerting to check for a pending interrupt before firing.
- Expose the distinction in the API/UI so a reviewer sees "waiting for you".

## Non-Goals

- Rewriting the checkpoint/projection read authority in general (AE-0336 / AE-0293).
- Changing the interrupt timeout or the auto-reject behaviour.
- Retro-classifying the 18 historical alerts beyond confirming the cause.

## Acceptance Criteria

- [ ] A run parked at an interrupt reports a status that says it is awaiting
      approval — never `approved` for the phase it has not finished.
- [ ] The reported status is derived from (or written atomically with) the
      checkpoint, with a test that drives the graph to an interrupt and asserts
      the reported status.
- [ ] Stuck-run alerting does not fire for a run with a pending `__interrupt__`.
- [ ] A test asserts the label cannot lag: after the interrupt is raised, the DB
      and checkpoint agree.
- [ ] The API contract change (if any) is reflected in the regenerated pinned
      artifacts.

## Gherkin Scenarios

```gherkin
Feature: Phase status reflects the real workflow position

  Scenario: Parked at the images approval gate
    Given the workflow raised an interrupt at the images gate
    When the project status is read
    Then it reports awaiting approval at the images phase
    And it does not report the images phase as approved

  Scenario: Alerting ignores a run waiting on a human
    Given a run has a pending interrupt
    When the stuck-run check evaluates it
    Then no stuck alert is raised

  Scenario: Approval advances both records together
    Given a run parked at the images gate
    When the reviewer approves
    Then the checkpoint and the database agree on the new phase
```

## Affected Areas

- Backend: carousel status read path, workflow engine interrupt handling, alerting
- Frontend: show "awaiting your approval" distinctly from "approved"
- Database: `phase_status` semantics (possible new value)
- API: status response; regenerate pinned artifacts if changed
- Tests: engine-level drive to an interrupt
- Docs: carousel workflow states
- Prompts/LLM: no
- Observability: alert rule update
- Deployment: no

## Dependencies

- Blocks: trustworthy operational signal for carousel runs
- Blocked by: none
- Related: AE-0336, AE-0293, AE-0320 (gate-approval deadlock)

## Implementation Plan

1. Test that drives the graph to the images interrupt and asserts the reported status (fails today).
2. Decide derive-vs-write-atomically; implement.
3. Add the `awaiting_approval` state and surface it.
4. Update the stuck-run alert to consult pending interrupts.
5. Confirm against the historical alert pattern.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested (interrupt raised then process restarted; approve race)
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-09-15

Ticket created from the AE-0330 session handoff (defect #12).

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
