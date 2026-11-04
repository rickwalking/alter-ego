# AE-0611 — A re-drafted slide keeps the old EN copy, and the slide rows keep the pre-retry card

Status: In Development
Tier: T2
Priority: Medium
Type: Bug
Area: Backend
Owner: Pedro
Agent Lane: developer → qa → release
Branch: fix/ae-0611-redrafted-slide-en-copy
Kanban Card: TBD
Created: 2026-11-04
Updated: 2026-11-04

## Goal

After the fail-closed retry re-drafts a PT slide, the EN copy describes the new PT, and the slide row shows the
new slide in both locales.

## Problem

Two follow-ups of AE-0602, which made the PT and EN cards keep the same shape.

1. A re-drafted slide keeps the EN heading and body of the old translation, whatever the card. EN then describes
   the old PT until a review catches it.
2. The slide rows keep the pre-retry card until the localized copy is written back, so anyone reading the rows in
   between sees a stale slide.

### Root cause: the EN copy

The content phase order is in `PhaseArtifactRunner._ensure_content_artifacts`:

1. Drafts, then `build_editorial_distribution_updates`: `_generate_en_translations` runs once, on the whole deck.
2. The copy budget step shortens fields and does not change what a slide says.
3. `build_fail_closed_review_updates` builds both locales. A slide that blocks gets one re-draft
   (`_replace_failing_drafts`). `_build_review` then rebuilds with the same `command.translations_en`.

`_resolve_en_source` takes the EN source from the draft's own `presentation_en` when it has one, and otherwise from
`translations_en`. So what the retry does to EN depends on the draft it gets back:

| Fresh draft | EN today |
|---|---|
| Plain copy (no `presentation_en`) | The old translation of the old PT: **this is the defect** |
| Labelled scaffold (`## PT` / `## EN`) | The old translation too, and the scaffold's EN section is ignored |
| Blob with both locales | The draft's own EN: fresh, nothing to fix |

The other two ways the phase changes PT were checked and do not have this problem:

- **Revise**: `slide_drafts` lands in the updates, so `_should_build_distribution` is true and the whole deck is
  translated again before the review, scoped revisions included.
- **Gate repair**: `run_gate_repair` rewrites only the fields a violation names, in that violation's locale, and keeps
  the meaning (ADR-030). It is not a re-draft, and it writes through `apply_localized_slide_edits`, which keeps the
  drafts, the translations and the reports in step. Not changed.

### Root cause: the rows

`apply_slide_drafts_to_database` runs inside the distribution step, before the retry, and `update_slide` commits each
row. `ensure_for_phase` projects the localized copy onto the rows only after `_ensure_content_artifacts` returns. So
the retry and the gate repair run (minutes of LLM calls) with the pre-retry rows committed and readable.

The final projection was also incomplete. `_merged_extras` merges the fresh EN over the row's old `translation_en`,
and the fresh EN never carries `content_kind`, so a row keeps the old translation's `content_kind: insight` after the
card is gone. `localized_from_slides` reads that key back, so copy rebuilt from the rows disagrees with PT.

## Scope

- Refresh the EN copy of the slides the fail-closed retry re-drafts.
- Write the rows right after a retry changes a slide, and drop the stale EN content kind from the row.

## Non-Goals

- The content gate, `translation_shape_mismatch`, any validator, limit or threshold.
- Prompts (the existing translation prompt takes any list of slides).
- Re-driving anything in prod.
- The caption, the blog, a row's long-form notes and its image prompt (see Follow-ups).

## Acceptance Criteria

- [x] AC1 A re-drafted slide shows EN copy translated from the new PT, and `translations_en` holds it.
- [x] AC2 Only re-drafted slides are translated, in one call per retry pass; no re-draft means no extra LLM call.
- [x] AC3 A failed or incomplete translation never leaves the old EN copy on the slide, and it is logged.
- [x] AC4 After a retry changes a slide, its row matches the new PT and EN before the gate repair runs.
- [x] AC5 The row's `translation_en` keeps no stale `content_kind`.
- [x] AC6 No gate, validator, limit, threshold or prompt change.

## Gherkin Scenarios

See `backend/tests/features/redrafted_slide_en_copy_ae0611.feature`.

## Delta

### ADDED

- `application/services/carousel/redrafted_translation.py`: `refresh_redrafted_translations`.
- `backend/tests/features/redrafted_slide_en_copy_ae0611.feature`
- `backend/tests/unit/application/test_redrafted_slide_en_ae0611.py`
- `backend/tests/unit/application/test_redrafted_slide_rows_ae0611.py`

### MODIFIED

- `application/services/carousel/content_fail_closed.py`: the retry refreshes the translations before its rebuild;
  `translate_slides` on the command.
- `application/services/carousel/phase_artifact_runner.py`: `_review_content` (the review, the scope and the row sync
  after a retry) and `_translate_slides`.
- `application/services/carousel/editorial_distribution_persist.py`: `_symmetric_translation` drops the stale
  `content_kind`.
- `docs/backend/slide-copy-validators.md`: one paragraph on this rule.

### REMOVED

- None.

## Affected Areas

- Backend: carousel content phase (fail-closed chain, runner wiring, row projection)
- Frontend: none
- Database: none (same columns, no migration)
- API: none
- Tests: unit, Gherkin
- Docs: `docs/backend/slide-copy-validators.md`
- Prompts/LLM: no prompt change; one extra fast-model call per retry pass that re-drafted a slide (see Decision Log)
- Observability: one new warning log
- Deployment: none

## Dependencies

- Blocks: none
- Blocked by: none
- Related: AE-0602, AE-0599, AE-0401

## Implementation Plan

1. Ticket, feature and failing tests.
2. `refresh_redrafted_translations` in the fail-closed chain, wired by the runner.
3. Row sync after the retry, and the stale content kind fixed in the projection.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-11-04 12:00

Ticket created, root cause traced.

### 2026-11-04 13:00

Fix in. 7 of the 11 new tests failed before it, and the row test fails again with the new sync turned off.

## Files Touched

See Delta.

## Test Evidence

- `test_redrafted_slide_en_ae0611.py` and `test_redrafted_slide_rows_ae0611.py`: 11 passed.
- Before the fix 7 of the 11 failed, among them the row's stale `content_kind: insight` and the old EN heading on a
  re-drafted slide. The other 4 pin what must not change (no call without a re-draft, for example).
- The 300 existing tests that import the touched modules pass. Run as that subset, one test fails on an unclosed event
  loop `ResourceWarning`. It lands on a different test each run and does the same on the base commit b8783527, so it is
  an existing leak, not this change.
- Light backend gates: see the dev summary. Full gate: lead's heavy slot.

## QA Report

Pending.

## Decision Log

- **Re-translate in the fail-closed chain, not "mark stale".** The translation step runs before the retry and nothing
  runs it again, so a stale mark would have no reader. The chain already holds what is needed.
- **One call per retry pass, re-drafted slides only.** The cost is one extra fast-model call (with the usual JSON
  retries and fallback) on a run where the retry re-drafted a slide, and a run has at most one retry pass. A deck with
  no re-draft, or with no stored translations, makes no call. No prompt change: the existing prompt takes any list.
- **Translate the PT the review will show.** A labelled scaffold draft is recovered first. The raw draft would send
  the `## PT` / `## EN` labels and the old EN section to the model.
- **A re-draft with its own `presentation_en` is left alone.** Its EN is already fresh, and the builder prefers it.
- **A failed translation is fail-closed.** The slide loses its stored translation, so EN falls back to the draft and
  the gate blocks it. Keeping the old EN would be the defect again, and raising would throw away a whole content
  phase for one slide. The same goes for a slide the answer skips. Both log `carousel_redraft_translation_missing`.
- **Rows: sync right after the retry, keep the end-of-phase sync.** Writing rows only from the final copy is not
  possible: the design tokens step needs the rows before the review. The sync runs only when the retry changed a
  slide, and after `keep_unscoped_slides`, so a scoped revision does not touch the other rows. A short window remains
  while the retry itself runs.
- **`content_kind` is dropped from the row's EN, never written.** PT rows do not store it either, so both sides infer
  it the same way.
- **Plain POV retry that adds a model-written card** (the second AE-0602 follow-up): the card now reaches EN with the
  refreshed translation, so the shape matches. The card text is not sent to the translator, the same as the first
  translation.

## Follow-ups (not in this ticket)

- The caption, the blog and the LinkedIn posts are built in the distribution step, before the retry, so they still
  describe the old slide. `blog_*` is out of bounds here.
- A row keeps the old slide's `long_form_notes` (PT and EN) and `image_prompt` after a retry: the projection preserves
  them on purpose, for owner edits.
- `review_translations` (`content_budget_step.py`) returns None when `slide_drafts` is in the updates, and the sanitize
  step always puts it there. So an ensure that neither regenerates nor rebuilds the distribution drops the stored
  translations, the very case its docstring says it keeps. Found while writing the row test. No re-draft is stale on
  that path, but its EN falls back to PT.
- The unclosed event loop in the test suite (see Test Evidence).

## Blockers

None.

## Final Summary

Pending.
