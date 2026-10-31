# AE-0512 — Rubrics polish: translated cards, real API data, phone layout, in-app leave dialog

Status: In Development
Tier: T1
Priority: Low
Type: Feature / UX
Area: Frontend
Owner: Pedro
Agent Lane: developer → qa → release
Branch: feat/ae-0512-rubrics-polish
Kanban Card: TBD
Created: 2026-10-31
Updated: 2026-10-31

## Goal

The `/dashboard/rubrics` page reads correctly in Portuguese and English, shows only data the rubrics API
returns, works on a 390 px phone and from the keyboard, and asks in an in-app dialog before the inline
editor drops unsaved changes.

## Problem

Listed by Pedro as a dashboard polish item (2026-10-22 triage). Findings confirmed in code:

- DQ-A-02: "Meets threshold" / "Below threshold" were hard-coded English in the PT list
  (`rubric-adapter.ts`).
- DQ-A-03: raw scale keys (`pass_fail`, `grade_a_f`, `1-10`) shown as scale names; ranges used a hyphen.
- DQ-A-04: at 390 px the card header was clipped (no wrap, `overflow: hidden`) and Excluir was unreachable;
  criteria rows had `min-w-[480px]`.
- DQ-A-05: the card showed only the first "Aplica-se a" content type.
- DQ-X-01: the card's "Peso: 1.0" and "active" status were hard-coded, not API data.
- DQ-A-07: the unsaved-changes guard on Cancel was a native `window.confirm`.
- DQ-A-13: Escape did not close the inline rubric editor.

## Scope

- Rubric card (adapter, panel, criteria table) and the rubric form's leave flow.
- pt/en strings for the card and the leave dialog.

## Non-Goals

- The link-click and tab-close guards of `useUnsavedChangesGuard` (shared with personas and the blog editor)
  stay browser-native; `beforeunload` cannot be styled.
- The personas form keeps its current Cancel guard.
- No backend or API change.

## Acceptance Criteria

- [x] AC1 pt/en strings translated: no "Meets threshold" in PT, no raw scale keys, ranges use an en dash
  ("1–10", "Fraco (1–2)").
- [x] AC2 the card shows every content type and the real API data: each criterion's own `weight`, and the
  `is_default` flag as a "Padrão"/"Default" badge. The API has no rubric-level weight and no status, so the
  fake "Peso: 1.0" and "active" were removed, not replaced.
- [x] AC3 at 390 px no clipping: the header wraps, criteria stack, Editar/Excluir are >= 44 × 44 px.
- [x] AC4 the Cancel guard is a styled in-app modal (`NeonConfirmDialog` → `NeonModal`: role="dialog",
  aria-modal, focus trap, Escape closes it, focus returns to the opener).
- [x] AC5 Escape cancels the editor, through the leave dialog when the form has changes.
- [x] AC6 Tab reaches each rubric's Edit then Delete in list order, with the button's visible focus ring.

## Gherkin Scenarios

See `frontend/tests/features/rubrics-polish-ae0512.feature` (9 scenarios). The AE-0452 threshold scenario
now reads with en dashes.

## Delta

### ADDED

- `frontend/src/lib/use-leave-confirm.ts` — leave-now-or-ask hook with Escape.
- `frontend/src/app/dashboard/rubrics/rubric-criteria-table.tsx`, `rubric-default-badge.tsx`,
  `use-rubric-labels.ts`.
- Tests: `rubric-panel.test.tsx`, `page-leave.test.tsx`; feature `rubrics-polish-ae0512.feature`.

### MODIFIED

- `rubric-adapter.ts` / `types.ts`: card data carries API keys and numbers; the page translates them.
- `rubric-panel.tsx`, `rubric-form.tsx`, `page.tsx` (narrower phone padding), `rubric-content-types-field.tsx`.
- `use-off-canvas.ts`: `useCloseOnEscape` exported for reuse.
- `pt.json` / `en.json` (`rubrics.panel`, `rubrics.form`).

### REMOVED

- `rubric-status-badge.tsx` (the fake "active" status), `RUBRIC_HEADER_HOVER_BG`, `thresholdLabel`.

## Affected Areas

- Backend: none
- Frontend: rubrics page
- Database: none
- API: none (read-only use of existing fields)
- Tests: vitest unit/page tests
- Docs: none
- Prompts/LLM: none
- Observability: none
- Deployment: none

## Dependencies

- Blocks: none
- Blocked by: none
- Related: AE-0452, AE-0455

## Implementation Plan

1. Gherkin first, then adapter/types, panel, leave dialog, tests, gates.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-10-31

Ticket created and implemented on `feat/ae-0512-rubrics-polish`. Before/after screenshots at 1440 and 390 px
captured with mocked API data (see the dev summary).

## Files Touched

See Delta.

## Test Evidence

See `.agent/reports/AE-0512.dev-summary.md`.

## QA Report

Pending.

## Decision Log

- Rubric weight/status: the API returns neither, so the card drops them and shows per-criterion weights and
  the default flag instead.
- The leave dialog reuses `NeonConfirmDialog`; the link-click guard stays native (shared hook, out of scope).

## Blockers

None.

## Final Summary

Pending.
