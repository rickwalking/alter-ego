# AE-0403 — Per-field validation errors and submit manual fixes on the review forms

Status: In Development
Tier: T1
Priority: P1
Type: Bug
Area: fullstack
Owner: Claude (hotfix)
Agent Lane: developer → release
Branch: fix/ae-0403-review-form-field-errors
Kanban Card: TBD
Created: 2026-10-16
Updated: 2026-10-16

## Goal

On both slide review forms, each validation error shows on the field that caused it, each slide form ends with its own error summary, and the owner can submit manual fixes. EN `<strong>` emphasis is no longer mangled when an edit is saved.

## Problem

Owner request (2026-10-16): "The review text page on the content should have a validation error at the bottom of each form. After fixing issues, it should have a button to submit manual fixes. Validation errors should show on individual fields."

On prod carousel 98a2e2f0, the publish-page slide editor refused a save and showed only one generic line (`slideEditor.blockingViolations`). Nothing was highlighted. The refusal came from our own save path: `sanitize_edited_slides` used `sanitize_display_input`, which strips `<` and `>`. That turned every EN `<strong>…</strong>` into `strong…/strong`, so the validator refused 6 EN bodies with `emphasis_markup_invalid`.

## Scope

- **Backend sanitizer:** the new `domain/copy_sanitize.sanitize_edited_copy` keeps case, PT `**`, and the exact `<strong>`/`</strong>` pair (lowercased). It still strips every other tag, stray `< > ( )` and the injection patterns, and caps the length. `sanitize_edited_slides` uses it on both wires (resume and the completed-project slide edit).
- **Backend response:** `CarouselSlideEditResponse.field_violations` (additive) restates every report violation with code, message, severity, slide_index, locale and field. For structured items it also gives `item_list`, `item_index` and `item_field`. `validation` is unchanged. The OpenAPI artifact is regenerated, and the frontend Zod schema (`slideFieldViolationSchema`) is mapped in the schema-drift gate.
- **Frontend, both forms** (publish-page `SlideTextEditSection` via the shared `SlideCopyEditor`, and the content-step `ContentPhaseReview`):
  - A flagged field gets a red border, `aria-invalid`, and the message under it (`aria-describedby`). This covers PT/EN heading and body, plus structured item bodies in the slide editor.
  - Each slide form ends with a per-slide summary ("Slide 9 · EN body: …").
  - The global notice links to every flagged slide. A refused submit focuses the first invalid field.
  - Codes map to pt/en i18n messages. Length codes include the backend `max N`. Unknown codes fall back to the backend message.
  - Editing a field clears that field's error.
  - **"Enviar correções manuais" / "Submit manual fixes"** button.
    - Publish page: it replaces Save after a refusal and is enabled once a field is edited. It re-submits the edits. On success the errors clear and the PDF rebuild runs. On a new refusal the new field errors show.
    - Content step: it saves through an edits-only revise (apply + re-validate + re-interrupt). It never approves.

## Non-Goals

- The content-step approve-with-edits 422 (`presentation_validation_blocked`) keeps its string `detail`. It stays backward compatible, and the manual-fixes path returns the violations through the workflow state.
- Structured item titles/icons have no editor today. Their violations show in the per-slide summary, not on a field.
- Parentheses stay stripped from edited copy (pinned by the AE-0314 XSS test). Out of scope.

## Acceptance Criteria

- [x] AC1: An EN edit containing `<strong>x</strong>` is saved unchanged; PT `**` too.
- [x] AC2: `<script>`, other tags and injection patterns are still stripped.
- [x] AC3: A refused slide-edit save returns `field_violations` with code, message, slide_index, locale, field, plus item list/index/sub-field for structured items; `validation` unchanged.
- [x] AC4: Both forms show each violation on its field (red border, `aria-invalid`, `aria-describedby` message).
- [x] AC5: Each slide form ends with a per-slide summary; the global notice links the flagged slides; a refused submit focuses the first invalid field.
- [x] AC6: Violation codes map to pt/en messages (limit included); unknown codes fall back to the backend message.
- [x] AC7: Editing a field clears its error.
- [x] AC8: "Submit manual fixes" re-submits; success clears errors and runs the PDF rebuild; a new refusal shows the new errors; at the content step it saves without approving.

## Gherkin Scenarios

- `backend/tests/features/review_form_field_errors_ae0403.feature`
- `frontend/tests/features/review-form-field-errors.feature`

## Delta

### ADDED

- `backend/src/rag_backend/api/routes/carousels/slide_edit_violations.py`
- `frontend/src/modules/editorial/workspace/lib/slide-field-errors.ts`
- `frontend/src/modules/editorial/workspace/hooks/use-slide-field-errors.ts`, `use-field-error-message.ts`
- `frontend/src/modules/editorial/workspace/components/slide-field-errors.tsx`
- `frontend/src/app/dashboard/create/workspace/phase-review/content-phase-locale-fields.tsx` (split out of `content-phase-review.tsx`)

### MODIFIED

- Backend: `domain/copy_sanitize.py`, `domain/constants/input_sanitizer.py`, `domain/constants/carousel_slide_edit.py`, `editorial_workflow_routes_sanitize.py`, `slide_edit.py`, `api/schemas/carousel_slide_edit.py`, `docs/architecture/openapi.json`
- Frontend: `slide-copy-editor.tsx`, `slide-text-edit-section.tsx`, `content-phase-review.tsx`, `create-phase-review.tsx`, `create-workflow-panel.tsx`, `use-edit-carousel-slides.ts`, `schemas/carousel.ts`, `scripts/check-schema-drift.mjs`, i18n `pt.json`/`en.json`

### REMOVED

- None.

## Affected Areas

- Backend: slide-edit sanitizer + response
- Frontend: publish-page slide editor, content-step review
- Database: none
- API: additive `field_violations` on `PATCH /carousels/{id}/slides`
- Tests: backend unit + `.feature`; frontend component/unit tests + `.feature`
- Docs: OpenAPI artifact, this ticket
- Prompts/LLM: none
- Observability: none
- Deployment: none

## Dependencies

- Blocks: none
- Blocked by: none
- Related: AE-0289, AE-0310, AE-0314, AE-0366

## Implementation Plan

1. Sanitizer + `field_violations` (backend, tests).
2. Shared field-error lib/hook/components; wire both forms; i18n.
3. Tests; individual gate runs; PR.

## QA Checklist

- [x] Security reviewed (only the exact `<strong>`/`</strong>` pair passes; every other tag, `< > ( )` and the injection patterns are stripped)
- [x] Code quality reviewed
- [x] Acceptance criteria validated
- [x] Edge cases tested (uppercase tag, tag with attributes, `a < b`, length cap, warning-only reports, field-less violations, a re-validation with the same violations)
- [x] Orphan/unfinished code checked

## Progress Log

### 2026-10-16

Implemented the hotfix. See `.agent/reports/AE-0403.dev-summary.md`.

## Files Touched

See Delta.

## Test Evidence

See `.agent/reports/AE-0403.dev-summary.md`.

## QA Report

Hotfix fast path. The gates were run one at a time; see the dev summary.

## Decision Log

- 2026-10-16: The content step's "submit manual fixes" uses the existing edits-only revise (`revise("", {editedLocalizedSlides})`, the AE-0310 escape hatch). It applies the edits, re-validates, re-interrupts and never approves. No new endpoint was added.
- 2026-10-16: `field_violations` is a new additive list, not new fields on the persisted `SlideValidationViolation` (`extra=forbid`, stored in checkpoints/JSONB). This keeps stored reports and `validation` byte-compatible.
- 2026-10-16: Field errors reset per validation run (a stamp), not per array identity. A state poll keeps the edited fields cleared, and a re-validation brings the errors back even when they are identical.
- 2026-10-16: The content-step approve 422 stays a string `detail` (backward compatible).
- 2026-10-16: Parentheses stay stripped from edited copy. The AE-0314 XSS test pins this, and changing it is out of hotfix scope.

## Blockers

None.

## Final Summary

PR #119 merged with CI green (including mutation). Gate evidence: `.agent/reports/AE-0403.dev-summary.md`.
