# AE-0414 — Content review UI: every slide, every flagged field editable, honest fixes

Status: In Review
Tier: T2
Priority: P1
Type: Bug
Area: Frontend
Owner: Claude (owner-requested QA fix wave 2026-10-16)
Agent Lane: developer → qa → release
Branch: fix/ae-0414-content-review-ui
Kanban Card: TBD
Created: 2026-10-17
Updated: 2026-10-17

## Goal

At the content gate the owner sees every slide, can edit every field a blocker points at (in
both locales), submits exactly what is on screen, and gets honest feedback from auto-fix and
from a refused manual fix, in the UI language.

## Problem

QA report `~/alter-ego-qa/2026-10-16-ui/REPORT.md` (re-verified on main 6e7c144):

- **B10** `resolveLocalizedSlides` used the draft presentations whenever ANY draft had both
  `presentation_pt`/`presentation_en` and `flatMap`-dropped every other draft, so slides 3-5
  vanished while `state.localized_slides` had all 7; their "Slide N" links had no card to focus.
- **B11** summary points / features / actions / tldr / insight rendered read-only; CTA extras
  showed "Campo estruturado: creator_name" with an empty value.
- **B04** the frontend never clamps, but it sent EVERY slide back, taken from the draft
  presentations. The GET state response truncates the drafts to v1 budgets on read (see the
  backend findings below), so the untouched slides were sent back cut mid-sentence.
- **B09** `AutoRepairButton` showed "Nenhuma correção determinística foi necessária." for any
  response without fixed diffs, ignoring `remaining_codes` and the blocking report.
- **B02 (frontend)** the 422 `edited_localized_slides_phase_not_allowed` code was rendered raw and
  the fire-and-forget `void revise(...)` rejection surfaced as an uncaught page error.
- **B29** budgets applied to `hero_lower_third_v1` only (every v1-v4 contract has the same
  budgets), so a v4 deck had no counter and accepted 5000 characters silently; no hint of the
  AE-0403 emphasis convention (PT `**`, EN `<strong>`).
- **B24 (part)** violation lines showed the backend's English message and the raw field path.

## Scope

1. Resolve slides per slide index: `localized_slides` wins (it is what the validator checks, the
   repair endpoint rewrites and edits merge into); a missing or malformed localized slide falls
   back to its draft presentation, then the legacy flat copy. No slide is ever dropped.
2. Structured items (title + body), string extras (tldr, CTA `creator_*`) and object extras with
   text fields (non-pov `insight`) are editable in both locales, with field-level error flags.
   The verified `pov_news` quote card stays read-only. Empty read-only values say "(vazio)".
3. Manual fixes send only the changed slides, verbatim; change detection covers every field.
4. Auto-repair: "could not fix N issues automatically; edit or request a revision" when blockers
   remain; "nothing to fix" only when none remain; a `noop` does not re-read state.
5. Resume 4xx codes map to `editorialWorkflow.errors.resumeCodes.*`; an edits-only revise
   resolves (error shown via the hook's `error`) instead of rejecting.
6. Budgets for every `hero_lower_third_v1..v4` and `pov_hook_v1` (items and CTA extras too); a
   live counter on every field that becomes an alert over budget; a per-locale emphasis hint, a
   mismatch warning and a "Convert emphasis" action.
7. Every presentation-validator code gets a pt/en message; the list shows the field label.

## Non-Goals

- Backend changes (AE-0413 owns them). Request contract unchanged (`edited_localized_slides`
  merged by `slide_index`).
- `create-workflow-panel.tsx`, `create-run-progress-banner.tsx`, the create form (AE-0415).

## Acceptance Criteria

- [x] AC1 (B10): all slides render when only some drafts carry presentations; localized copy
  wins per slide; the "Slide N" link focuses that slide card.
- [x] AC2 (B11): flagged summary-point/feature/action fields and CTA/tldr/insight text are
  editable in PT and EN and reach the manual-fix payload; CTA values are visible.
- [x] AC3 (B04): the payload carries only changed slides with untouched copy byte-identical.
- [x] AC4 (B09): a `noop` with blockers says it could not fix N issues; no "nothing needed".
- [x] AC5 (B02 FE): 422 codes show translated copy; no uncaught rejection for manual fixes.
- [x] AC6 (B29): live counter + over-budget alert on v4; per-locale emphasis hint + convert.
- [x] AC7 (B24 part): violation lines are translated (pt/en) with a field label.

## Gherkin Scenarios

`frontend/tests/features/content-review-manual-fixes-ae0414.feature`

## Delta

### ADDED

- `lib/presentation-copy-budgets.ts` (budget tables per policy, item/extra budgets, `measureBudgetUsage`)
- `lib/presentation-emphasis.ts` (per-locale convention, mismatch, convert)
- `phase-review/content-phase-copy-field.tsx`, `content-phase-structured-fields.tsx`, `content-phase-violations.tsx`
- `applySlideExtraEdit`, `changedLocalizedSlides`; i18n `review.copyField.*`, `autoRepair.remaining`,
  `errors.resumeCodes.*`, 18 more `fieldErrors.codes.*`

### MODIFIED

- `resolveLocalizedSlides` (per-slide merge), `slidesHaveCopyChanges` (every field)
- `content-phase-review.tsx`, `content-phase-locale-fields.tsx`, `auto-repair-button.tsx`
- `use-editorial-workflow(-resume).ts` (code mapping; edits-only revise resolves)

### REMOVED

- Budget helpers moved out of `presentation-review-utils.ts`; i18n `review.fieldBudget`.

## Affected Areas

- Frontend: content gate review, auto-repair button, workflow hook. Backend/API/DB: none.

## Dependencies

- Related: AE-0413 (backend manual fixes; see the findings below), AE-0415 (panel/create form), AE-0403, AE-0407.

## Backend findings for AE-0413 (not fixed here, frontend-only ticket)

1. `build_editorial_workflow_state_response` (`api/routes/carousels/editorial_workflow_routes_response.py`)
   runs `SanitizeWorkflowStateCommand(state=state)` with the DEFAULT policy (v1) and
   `rebuild_validation=True` on every GET: it truncates draft copy to the budgets
   (`_truncate_visible_copy`, word-boundary cut → B04 "…mostra que vaga"), REBUILDS
   `localized_slides` + `presentation_validation` from the drafts (discarding repaired/edited
   localized copy) and sets `presentation_policy_version` to `hero_lower_third_v1` → the B09
   "v4 → v1" flip right after the auto-repair refresh (SSE payloads still say v4).
2. `resume_editorial_workflow` bumps `lock_version` BEFORE `ensure_structured_feedback_allowed`
   raises the 422; if that bump commits, the refreshed lock resets the panel's local edits
   (B02 "edits reverted").

## QA Checklist

- [x] Security reviewed (no new input path; edits still go through the backend sanitizer)
- [x] Code quality reviewed
- [x] Acceptance criteria validated
- [x] Edge cases tested
- [x] Orphan/unfinished code checked

## Progress Log

### 2026-10-17

Ticket created, causes re-verified on main, fixed with tests; gates run locally.

## Test Evidence

See the PR body (`bash scripts/ci/gates.sh frontend`).

## Decision Log

- Localized copy wins over the draft per slide (the orchestrator brief suggested the opposite):
  violations, repair and edit merge all target `localized_slides`, and the drafts are the
  truncated copy on GET, so preferring drafts reproduces B04.
- Only changed slides are sent: the backend merges by `slide_index`, so this is
  contract-compatible and an untouched slide can never be overwritten.

## Blockers

None.

## Final Summary

See the PR.
