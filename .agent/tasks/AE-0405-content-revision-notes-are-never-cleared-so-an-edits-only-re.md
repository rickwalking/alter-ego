# AE-0405 — Content revision notes are never cleared, so an edits-only resubmit can regenerate and overwrite edited copy

Status: In Development
Tier: T1
Priority: P1
Type: Bug
Area: backend
Owner: developer agent
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

- [x] AC1: After a feedback revise regenerates content, the note is in history and no longer in the active notes.
- [x] AC2: An edits-only content resubmit after an earlier feedback revise keeps the edited copy byte-for-byte and does not call the drafting model.
- [x] AC3: A new feedback after AC2 regenerates with only that new note.
- [x] AC4: Autopilot gate feedback is tagged, applied once, and not re-fed afterwards.
- [x] AC5: The resume-on-approval path does not regenerate content when there are no unapplied notes.
- [x] AC6: History is queryable for the persona feedback loop.

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

Implementation (hotfix fast path), branch `fix/ae-0405-content-feedback-lifecycle`:

- **Root cause, deeper than the notes.** A real-graph experiment showed that LangGraph replays the
  whole content node on every resume, and that an interrupted node's return value is never committed.
  The content ensure (which can regenerate every slide) therefore ran again on approve, on revise and
  on an edits-only resubmit. With the accumulated notes it regenerated again and committed drafts
  nobody reviewed, which is the 98a2e2f0 symptom.
- **Feedback lifecycle** (`content_feedback_lifecycle.py`): active notes are tagged (`source`,
  `added_at`) in `phase_feedback_notes`. The regeneration that uses them moves them to
  `phase_feedback_history` (`applied`). `feedback_history(state, phase)` is the query (AC6).
- **Durable parked review** (`carousel_workflow_nodes.py`, `carousel_content_park.py`, engine): the
  content node carries that pass's artifact updates on the interrupt payload. The engine saves them
  to the checkpoint once the graph parks (marker `content_artifacts_parked`, `content_approved=False`)
  and re-parks. The resume replay reuses them: no ensure and no LLM call (AC2, AC5).
- **Autopilot**: `editorial_driver` sends `feedback_source=autopilot` with the gate feedback, and
  `prepare_resume_workflow` files it tagged (AC4). An active autopilot note is dropped when the
  content gate is approved.
- **Migration on read**: `prepare_resume_workflow` settles legacy untagged content notes to
  `migrated` on every resume, unless the content phase is `failed`.

## Files Touched

- `backend/src/rag_backend/application/services/carousel/content_feedback_lifecycle.py` (new)
- `backend/src/rag_backend/domain/constants/content_feedback.py` (new)
- `backend/src/rag_backend/agents/carousel_content_park.py` (new)
- `backend/src/rag_backend/agents/carousel_workflow_engine.py`
- `backend/src/rag_backend/agents/carousel_workflow_nodes.py`
- `backend/src/rag_backend/application/services/carousel/editorial_workflow_feedback.py`
- `backend/src/rag_backend/application/services/carousel/editorial_workflow_service_helpers.py`
- `backend/src/rag_backend/application/services/carousel/editorial_workflow_types.py`
- `backend/src/rag_backend/application/services/carousel/phase_artifact_runner.py`
- `backend/src/rag_backend/application/services/carousel/workflow_state.py`
- `backend/src/rag_backend/modules/autopilot/infrastructure/editorial_driver.py`
- `backend/tests/features/content_feedback_lifecycle_ae0405.feature` (new)
- `backend/tests/unit/agents/content_feedback_flow_ae0405.py` (new, harness)
- `backend/tests/unit/agents/test_content_feedback_replay_ae0405.py` (new)
- `backend/tests/unit/application/test_content_feedback_lifecycle_ae0405.py` (new)
- `backend/tests/unit/modules/autopilot/test_editorial_driver_outcomes.py`
- `backend/tests/unit/agents/test_carousel_workflow_phases.py` (the compiled-graph stub gets `checkpointer = None`)
- `docs/backend/content-feedback-lifecycle.md` (new), `backend/CLAUDE.md` (doc link)

## Test Evidence

TBD.

## QA Report

Pending.

## Decision Log

- 2026-10-16: Treat a note as consumed by the regeneration that used it, rather than clearing all notes on approval. That keeps the human-correction history for the persona loop.
- 2026-10-16 (dev): **The notes are only half the bug.** LangGraph replays the interrupted content node on resume, and that pass's return value is never committed. Consuming notes inside the ensure alone would be thrown away at the interrupt, and the replay would regenerate again. Chosen fix: save the parked pass's artifacts to the checkpoint and reuse them on replay. Rejected: splitting the node into generate and review nodes. That is the cleaner LangGraph shape, but it changes the graph topology under live checkpoints parked at `content` and every send-back route, which is too wide for a hotfix.
- 2026-10-16 (dev): The artifacts travel on the interrupt payload (only the engine reads payloads; `get_state` merges a fixed key list). After the checkpoint write the engine re-parks with `ainvoke(None)`. The write drops the pending interrupt, and without the re-park `get_state` would stop reporting `awaiting_human` and `is_parked_before_node` would call it a dead run. The replay costs no LLM call.
- 2026-10-16 (dev): The park write also sets `content_approved=False`. A final-review send-back leaves it True, and a checkpoint write at the parked content review (the park write, or the existing `persist_phase_feedback`) then routed past the content gate. A test pins this.
- 2026-10-16 (dev): Legacy migration is "settle on resume": untagged notes move to the history as `migrated` unless the content phase is `failed` (its regeneration never ran). An untagged note can only exist in pre-AE-0405 state, and the checkpoint holds one only after the regeneration that used it.
- 2026-10-16 (dev): Autopilot notes are tagged through `structured_feedback.feedback_source` (the autopilot does not go through the HTTP schema). A client could also send it; the only effect is the tag. "Dropped when the gate reason no longer holds" means an active autopilot note is dropped when the content gate is approved.
- 2026-10-16 (dev): AC6 "queryable" = `feedback_history(state, phase)` over the checkpoint state. The API response is unchanged ("API: none expected"), so the OpenAPI and Zod schema-drift gates are untouched.
- 2026-10-16 (dev): Timestamps use the wall clock inside the artifact runner (an application service). The marker stops the pass from being replayed, so no non-determinism reaches the graph.
- 2026-10-16 (dev): `carousel_workflow_nodes.py` (520 lines) and `phase_artifact_runner.py` (644) were already over the 400-line rule. Moving the content node to its own module was tried and reverted: it adds an agents→application import pair (`CarouselWorkflowState`), which the import contract, the arch ratchet and the integrity gate block. So nodes grows by about 40 lines; the park logic is in the new `carousel_content_park.py` (no application import), and the runner gained no lines. A follow-up could move `CarouselWorkflowState` to a layer agents may import, then split the nodes file.
- 2026-10-16 (dev): Out of scope, reported: a send-back resume from the approved-hold park goes through `persist_phase_feedback` → `engine.update_state` with `as_node` inferred as `approved_hold`. That completes the hold node, so the graph ends and the send-back is lost (the documented `as_node` footgun; it predates this change). Follow-up ticket recommended.

## Blockers

None.

## Final Summary

Pending.
