# Content revision notes and the parked content review (AE-0405)

A content revision note steers **one** regeneration. Manual edits never regenerate the
slide copy.

## Why

- `persist_phase_feedback` appended every note to `phase_feedback["content"]` forever, and
  `PhaseArtifactRunner` fed **all** of them to any content re-run. Any re-run that had notes
  regenerated the drafts.
- LangGraph replays the **whole** interrupted node on resume. The content node runs its
  ensure (which can regenerate every slide) before its review `interrupt()`, and an
  interrupted node's return value is never committed. So every resume (approve,
  edits-only resubmit, revise) ran the ensure again. With the old notes it regenerated
  again and committed drafts nobody reviewed. On carousel 98a2e2f0 this replaced
  hand-fixed slides 3 and 8 when the content was approved.

## State

| Field | Meaning |
|-------|---------|
| `phase_feedback[phase]` | Active note texts (API shape unchanged). |
| `phase_feedback_notes[phase]` | The same notes with `source` (`human` / `autopilot`) and `added_at`. |
| `phase_feedback_history[phase]` | Consumed notes: `status` `applied` / `unchanged` / `dropped` / `migrated`, plus `settled_at`. Read it with `content_feedback_lifecycle.feedback_history(state, phase)`. |
| `content_artifacts_parked` | True while the graph is parked at the content review and that pass's artifacts are saved. |

## Lifecycle

1. **Filing a note.** `persist_phase_feedback` files a revise note as active and tagged. The
   autopilot sends `structured_feedback.feedback_source = "autopilot"`.
2. **Applying a note.** When the content ensure regenerates with the active notes, it moves
   them to the history as `applied`. A failed regeneration (invalid JSON) keeps them active
   for the retry. AE-0430: the regeneration request also carries the content gate's
   blocking violations (one line each: slide, locale, field, rule and limit), the targeted
   gate repair runs after it (see `slide-copy-validators.md`), and the note is recorded as
   `unchanged` instead of `applied` when the visible slide copy did not change.
3. **Parking.** The content node puts that pass's artifact updates on the interrupt payload
   (`parked_artifact_updates`). Once the graph parks, `CarouselWorkflowEngine` writes them to
   the checkpoint, sets `content_artifacts_parked` and `content_approved=False`, then re-parks
   with `ainvoke(None)` (the write drops the pending interrupt). Resetting `content_approved`
   matters: a final-review send-back left it True, and a checkpoint write at the parked
   content review then routed past the content gate.
4. **Replay.** On resume the content node sees the marker and reuses the saved artifacts:
   no ensure, no LLM call. The reviewer's edits are applied on top, and the node finishes
   with the marker reset. A revise then re-enters the content node, which runs its ensure:
   it regenerates only when there are new notes, otherwise it re-validates the edited copy.
5. **Settling stale notes on resume.** `prepare_resume_workflow` runs this on every action:
   - Legacy untagged notes (from before AE-0405) already steered the last regeneration, so
     they move to the history as `migrated`. The exception is a content phase that is
     `failed`: there the regeneration never ran and the notes stay active.
   - An active autopilot note is `dropped` when the content gate is approved, because the
     reason it was written for no longer holds.

## Manual fixes and the content gate phase (AE-0413)

- **The first content gate accepts manual fixes.** The content node is interrupted, so its
  return value is never committed: on the first content gate the stored `current_phase`
  still said `outline`, and the structured-feedback guard (`read_checkpoint_phase`) 422'd
  `edited_localized_slides` (`edited_localized_slides_phase_not_allowed`). The guard now reads
  the phase of the gate the graph is parked at (`checkpoint_gate_phase`: the pending node,
  except the approved hold), and the parked content checkpoint stores `current_phase=content`.
- **Manual fixes apply and re-validate only.** A revise that carries only
  `edited_localized_slides` (no new note, no send-back) sets `content_artifacts_parked` when
  the node finishes, so the next content entry reuses the edited, re-validated copy. Before,
  the re-entry ran the content ensure: it rebuilt every localized slide from the PT drafts
  (EN fell back to the PT copy, structured items were dropped) and re-drafted blocking slides
  with the LLM. A revise with a new note still regenerates (with the edits as the previous
  drafts). Log: `content_manual_fixes_kept`.
- **A content re-entry without regeneration keeps the stored EN translations**
  (`translations_en`); the fail-closed single-slide re-draft receives the active notes.
- **Where a used note goes.** `phase_feedback.content` lists the *active* notes only, so it is
  `[]` after a revision used the note. The state response now also serves
  `phase_feedback_history` (`{phase: [{note, source, added_at, status, settled_at}]}`).

Logs: `content_feedback_applied`, `content_feedback_settled`, `content_artifacts_parked` and
`content_artifacts_replay_reused`.

Tests: `backend/tests/features/content_feedback_lifecycle_ae0405.feature`,
`tests/unit/agents/test_content_feedback_replay_ae0405.py` (real engine and real runner; the
drafting model is a spy) and `tests/unit/application/test_content_feedback_lifecycle_ae0405.py`.
