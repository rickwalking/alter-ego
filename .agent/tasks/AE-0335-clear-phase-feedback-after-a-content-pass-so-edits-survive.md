# AE-0335 — clear phase feedback after a content pass so reviewer edits survive

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

Consume send-back notes **once**. A content pass that has acted on its feedback
must clear it, so later passes stop regenerating copy and stop overwriting the
reviewer's edits.

## Problem

`phase_feedback["content"]` is **append-only and never cleared**.
`editorial_workflow_feedback.persist_phase_feedback` appends
(`phase_feedback[phase] = [*prior_feedback, trimmed]`, line 59) and nothing
anywhere deletes the key. `phase_artifact_runner._content_revision_notes`
(line 463-470) reads it on **every** content-node execution.

Consequence observed live on carousel `dcaa5fef…`: once a reviewer sent a slide
back from the content gate, **every subsequent pass through the content node
regenerated all drafts** — roughly 40 minutes per pass (7 slides × ~5 min on
GLM 5.2) — and each regeneration **overwrote the reviewer's edits** with fresh
LLM copy. The operator workaround was to stop editing at the content gate
entirely and edit at the **design** gate instead, because the design pass only
applies tokens and re-validates.

So the product currently has a gate whose edits are guaranteed to be destroyed,
and an expensive one: the notes stay live forever, so cost and latency are paid
on every pass for a revision that was already applied.

## Scope

- Clear (or mark consumed) `phase_feedback[PHASE_CONTENT]` once a content pass
  has regenerated using those notes — written in the **same state update** as
  the regenerated drafts so the two cannot diverge.
- Same treatment for any other phase that reads `phase_feedback` for a
  regeneration decision; audit all readers.
- Preserve the notes for audit: move them to a `phase_feedback_history` (or
  equivalent append-only record) rather than dropping them, so the reviewer trail
  survives.
- Idempotency: replaying the same checkpoint must not re-consume already-consumed
  notes (workflow state changes must be idempotent — root `CLAUDE.md`).

## Non-Goals

- Changing the send-back UX or the revision cap (5/phase).
- Fixing where the edits are written (AE-0336 covers checkpoint vs DB projection).
- The `current_phase` vs `target_phase` keying bug — that is its own known issue;
  this ticket is about the lifetime of the notes, not which phase they land on.

## Acceptance Criteria

- [ ] After a content pass that regenerates from notes, `phase_feedback["content"]`
      is empty in the resulting state.
- [ ] The notes are retained in an audit field; the reviewer trail is not lost.
- [ ] A second pass through the content node with no new feedback does **not**
      regenerate drafts.
- [ ] Reviewer edits made at the content gate survive a subsequent pass.
- [ ] Clearing and regeneration are one atomic state update; replaying the
      checkpoint does not double-consume.
- [ ] Engine-level test drives: send back → regenerate → notes cleared → next
      pass is a no-op.

## Gherkin Scenarios

```gherkin
Feature: Send-back notes are consumed once

  Scenario: A content pass consumes its feedback
    Given the reviewer sent a slide back with a note
    When the content node regenerates the drafts
    Then the content feedback list is empty afterwards
    And the note is recorded in the feedback history

  Scenario: A later pass does not regenerate
    Given the content feedback list is empty
    When the workflow passes through the content node again
    Then no drafts are regenerated

  Scenario: Reviewer edits survive
    Given the reviewer edited slide 3 at the content gate
    When the workflow passes through the content node again
    Then slide 3 still holds the reviewer's text

  Scenario: Replay does not double-consume
    Given a checkpoint taken after the notes were consumed
    When the checkpoint is replayed
    Then the drafts are not regenerated a second time
```

## Affected Areas

- Backend: `application/services/carousel/phase_artifact_runner.py`, `editorial_workflow_feedback.py`, `workflow_state.py`
- Frontend: no (state shape exposed via `api/schemas/carousel_workflow.py` — check the contract)
- Database: possible new audit field
- API: `phase_feedback` is in the workflow schema — regenerate the pinned artifacts if the contract changes
- Tests: engine-level drive + unit
- Docs: carousel workflow guide
- Prompts/LLM: no
- Observability: log consume events
- Deployment: no

## Dependencies

- Blocks: usable content gate
- Blocked by: none
- Related: AE-0336, AE-0334, `carousel-send-back-feedback-keying-bug` (current_phase vs target_phase)

## Implementation Plan

1. Engine test that reproduces: send back → pass → pass → assert regenerated twice (fails today).
2. Add the consume-and-archive step inside the same update that writes the drafts.
3. Audit other `phase_feedback` readers; apply the same lifetime.
4. Idempotency test over a replayed checkpoint.
5. If the API schema changes, regenerate `openapi.json` + the workflow snapshots
   (4 regenerations per the backend pinned-artifact rule).

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested (multiple notes, note added mid-pass, replay)
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-09-15

Ticket created from the AE-0330 session handoff (defect #8). Confirmed:
`editorial_workflow_feedback.py:59` appends, `phase_artifact_runner.py:463` reads,
no writer clears.

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
