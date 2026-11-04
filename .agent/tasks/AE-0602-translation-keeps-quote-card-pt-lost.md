# AE-0602 — The EN translation keeps a quote card that the PT draft lost

Status: In Development
Tier: T1
Priority: Medium
Type: Bug
Area: Backend
Owner: Pedro
Agent Lane: developer → qa → release
Branch: fix/ae-0602-pov-quote-card-shape
Kanban Card: TBD
Created: 2026-11-03
Updated: 2026-11-04

## Goal

The PT and EN payloads of a slide always have the same shape, so the content gate never blocks a carousel on
`translation_shape_mismatch` for a card one locale dropped.

## Problem

Found in the read-only prod triage of 2026-11-02 (AE-0599). The autopilot POV carousel 41c4f437 was blocked
at its first content gate by one violation, `translation_shape_mismatch` on slide 4: the EN translation still
carried a quote card (`insight`) that the PT draft no longer had. No copy-budget or emphasis code is involved
(AE-0599 ruled that out).

### Root cause

The translation is made once, and the fail-closed retry can change the PT draft after it. The content phase
runs in this order (`phase_artifact_runner`):

1. **Drafts.** `place_quote_cards` puts the verified card on the PT draft of a `pov_news` slide.
2. **Translation.** `_generate_en_translations` runs, and the model's answer never carries `insight`:
   `_with_pt_structure` copies the card from the PT draft and `with_en_quote_cards` swaps in `text_en`. So an EN
   card can only come from a PT draft that had one at this moment.
3. **Copy budget step.** It does not touch the structure.
4. **Fail-closed review.** `build_fail_closed_review_updates` builds both locales. A slide that blocks gets
   ONE re-draft (`build_slide_draft_retry`), and `_without_quote_card` strips the card from the fresh draft,
   because a single-slide retry cannot see the deck's cap of 2 cards. `_build_review` then rebuilds with the
   same `translations_en`, which nothing updates, so the stale translation brings the card back in EN only.

This is the only path in the content phase that takes a card off a PT draft after the translation. It matches
the prod facts: AE-0599 found PT "recovered from a scaffold as an empty feature list", which is what a fresh
scaffold draft becomes through `recover_parse_failures` / `normalize_canonical_shape` (`features:0`), against EN
`insight:1`. The prod checkpoint was not re-read: the proof is the code path plus a test that gives the same
shapes through the real chain. Draft normalization and the deterministic repair are ruled out: a draft that
still has its card keeps it in PT through both (`_infer_content_kind` gives `insight`).

## Scope

- Find the step where the PT and EN shapes diverge for a quote card, with a failing test built from the
  41c4f437 slide-4 shape (synthetic text, no user content).
- Fix it on the generation side so both locales keep the same cards.

## Non-Goals

- Changing the content gate or `translation_shape_mismatch` (the validator is right to block).
- Re-driving 41c4f437 in prod (owner's decision, separate).
- Re-translating a re-drafted slide (see Decision Log and Follow-ups).

## Acceptance Criteria

- [x] AC1 A slide whose PT draft drops a quote card never reaches the gate with the card only in EN.
- [x] AC2 A failing-then-passing test reproduces the 41c4f437 slide-4 shape.
- [x] AC3 No gate, validator, limit or threshold change.

## Gherkin Scenarios

See `backend/tests/features/pt_en_same_cards_ae0602.feature` (the draft's scenario plus the retry path, the kept
card, the content kind and PT replacing the card with items).

## Delta

### ADDED

- `backend/tests/features/pt_en_same_cards_ae0602.feature`
- `backend/tests/unit/application/test_pt_en_same_cards_ae0602.py`

### MODIFIED

- `application/services/carousel/localized_slide_builder.py`: `_without_en_only_card`, applied where the EN
  payload is built from a translation.
- `tests/unit/application/test_content_gate_after_budget_ae0599.py` and
  `tests/features/content_gate_after_copy_budget_ae0599.feature`: the 41c4f437 test pinned this defect ("the
  gate still reports it"). It now expects no violation at all, which is a stricter assertion.
- `docs/backend/slide-copy-validators.md`: one paragraph on this rule.

### REMOVED

- None.

## Affected Areas

- Backend: carousel localized slide builder (content review build)
- Frontend: none
- Database: none
- API: none
- Tests: unit, Gherkin
- Docs: `docs/backend/slide-copy-validators.md`
- Prompts/LLM: none
- Observability: none
- Deployment: none

## Dependencies

- Blocks: none
- Blocked by: none
- Related: AE-0599, AE-0430, AE-0401

## Implementation Plan

1. Trace the phase order and write the root cause (above).
2. Feature first, then tests that fail on the old code, then the fix.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-11-04

Root cause traced to the fail-closed retry. Feature and tests written (5 of 6 failed on the old code; the
sixth pins that a card PT still has stays), fix applied in the localized builder.

## Files Touched

See Delta.

## Test Evidence

See `.agent/reports/AE-0602.dev-summary.md`.

## QA Report

Pending.

## Decision Log

- **Drop the EN-only card, do not re-translate.** The chain has no translator: re-translating from the final PT
  means a new model call inside the fail-closed retry, with its own failure, retry and budget handling, and
  the deterministic path fixes the blocker with no new failure mode. PT is the source, so a card PT lost has no
  claim on EN. If PT gained items instead, the gate repair already copies and translates them
  (`fill_missing_en_structure`).
- **Fix it in the builder, not only in the retry.** `build_localized_slide_with_failures` is where every path
  (first build, retry rebuild, copy budget rebuild, state rebuilds) joins a PT draft to a translation, so AC1
  holds on all of them, including a checkpoint whose draft had already lost the card. It also needs no change to
  the state: `_symmetric_translation` drops the stale `insight` from the slide row's `translation_en` once the
  localized EN has none, and the rebuild from the state applies the same rule.
- **EN's content kind follows PT.** A translation can carry `content_kind: insight`, copied from the old draft.
  Keeping that without the card would leave `insight:1` in EN. A missing kind is recovered by the existing
  `normalize_canonical_shape`, the same way as PT.
- **A stored pair of `presentation_pt` + `presentation_en` is left alone.** It holds no translation to go
  stale, the blob builder writes no card, and reviewer edits go through it, so the validator stays the check there.

## Follow-ups (not in this ticket)

- A re-drafted slide keeps the EN heading and body of the old translation, whatever the card. The EN then
  describes the old PT until a review catches it. This is older than this ticket and is not a shape problem.
- The reverse case, a retry adding a model-written card in plain POV mode (PT card, none in EN), is not changed:
  the gate blocks and the gate repair fills EN.

## Blockers

None.

## Final Summary

The fail-closed retry takes the quote card off a re-drafted PT slide, but the stored EN translation still had it.
The localized builder now drops an EN card its PT slide does not have, and EN takes PT's content kind. The
41c4f437 shape reaches the gate with no violation. The gate and validators are unchanged.
