# AE-0405 — Content revision notes are never cleared, so an edits-only resubmit can regenerate and overwrite edited copy

Status: Ready
Tier: T1
Priority: P1
Type: Bug
Area: backend
Owner: Unassigned
Agent Lane: developer → qa → release
Branch: fix/ae-0405-content-feedback-lifecycle
Kanban Card: TBD
Created: 2026-10-16
Updated: 2026-10-16

## Goal

A content revision note applies to the regeneration it was written for, and only that one. Submitting manual edits never regenerates the slide copy.

## Problem

- **Notes accumulate.** `editorial_workflow_feedback.persist_phase_feedback` appends every content feedback to `phase_feedback["content"]` and nothing ever clears it.
- **Any re-run regenerates.** `PhaseArtifactRunner` (`_content_revision_notes` → `ContentRegenInputs.revision_notes`) feeds ALL accumulated notes into any content re-run, and a re-run with notes regenerates the drafts.

**Consequences:**
- An edits-only resubmit at the content step (AE-0403 "Enviar correções manuais") after an earlier feedback revise could regenerate the copy and overwrite the owner's edits. This was flagged by the AE-0403 worker and not changed there.
- Stale autopilot notes keep steering later regenerations.

**Prod evidence (carousel 98a2e2f0, run b241ded5, 2026-10-16):**
- `phase_feedback["content"]` still holds three notes:
  1. the owner's thesis note;
  2. the autopilot note "The content gate failed the autopilot check. Reason: persona_score_below_threshold. Measured: 5.8." (from the 0-10 score-scale bug fixed in AE-0398, so it was wrong);
  3. the owner note again.
- Every later content re-run received all three, including the re-run on approval resume. That re-run replaced hand-fixed slides 3 and 8 with fresh drafts (slide 8 came back as a fenced JSON blob).

## Scope

1. **Feedback lifecycle.** A revision note is consumed by the regeneration that uses it:
   - Mark it applied (or move it to an `applied_feedback` history) once the content node regenerates with it.
   - Keep the history for the audit and feedback loop (CLAUDE.md "Record all human corrections").
2. **Edits-only paths never regenerate.**
   - A resubmit or resume that carries edited slides but no new feedback must persist the edits and re-validate.
   - It must not run content regeneration, even when older notes exist.
3. **Autopilot notes.**
   - Gate feedback the autopilot writes (revise reasons) is tagged as autopilot feedback.
   - It is dropped once its revise ran, or when the gate reason no longer holds.
4. **Migration of existing state.** Projects whose content notes all predate their last regeneration are treated as applied. No data loss: they move to the history.

## Non-Goals

- Changing the revise prompts or the persona scoring.

## Acceptance Criteria

- [ ] AC1: After a feedback revise regenerates content, the note is in history and no longer in the active notes.
- [ ] AC2: An edits-only content resubmit after an earlier feedback revise keeps the edited copy byte-for-byte and does not call the drafting model.
- [ ] AC3: A new feedback after AC2 regenerates with only that new note.
- [ ] AC4: Autopilot gate feedback is tagged, applied once, and not re-fed afterwards.
- [ ] AC5: The resume-on-approval path does not regenerate content when there are no unapplied notes.
- [ ] AC6: History is queryable for the persona feedback loop.

## Gherkin Scenarios

To write first: `backend/tests/features/content_feedback_lifecycle_ae0405.feature` (happy, edits-only, stale autopilot note, approval resume, migration).

## Delta

### ADDED

- The feature file and unit tests

### MODIFIED

- `application/services/carousel/editorial_workflow_feedback.py`
- `application/services/carousel/phase_artifact_runner.py`
- The content resume/edit paths (AE-0403 manual fixes)

### REMOVED

- None.

## Affected Areas

- Backend: editorial workflow content phase
- Frontend: none expected
- Database: none (checkpoint state only)
- API: none expected
- Tests: unit + feature
- Docs: llm/editorial workflow docs if they describe feedback
- Prompts/LLM: fewer, correct revision notes
- Observability: log applied/dropped notes
- Deployment: none

## Dependencies

- Blocks: safe content-step "Submit manual fixes" (AE-0403)
- Blocked by: none
- Related: AE-0403, AE-0401, AE-0392, AE-0398

## Implementation Plan

1. Write the feature file.
2. Feedback lifecycle (applied/history).
3. Edits-only guard.
4. Autopilot tagging.
5. State migration on read.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-10-16

Ticket created from the AE-0403 worker's follow-up risk and the 98a2e2f0 evidence.

## Files Touched

TBD.

## Test Evidence

TBD.

## QA Report

Pending.

## Decision Log

- 2026-10-16: Treat a note as consumed by the regeneration that used it, rather than clearing all notes on approval. That keeps the human-correction history for the persona loop.

## Blockers

None.

## Final Summary

Pending.
