# AE-0622 — Checklist slide editor shows and keeps each item's body

Status: Dev Complete
Tier: T1
Priority: High
Type: Bug
Area: Frontend
Owner: Claude
Branch: fix/checklist-editor-shows-item-body
Created: 2026-11-09
Updated: 2026-11-09

## Goal

The owner can see and fix every summary-point field the summary rule checks, on checklist slides too.

## Problem

On a checklist summary slide the editor showed one line per item (the title) and hid the body; editing a line
also emptied the body. The summary rule (`summary_points_missing`) needs at least 3 points with a title and a body,
and pins its error on the first missing part, here `summary_points[0].body`. The owner saw "O slide de resumo precisa
dos pontos de resumo" under a line that had its text, with no field to fix. Prod carousel 1c279329 (slide 8) had 3 of
4 PT points without a body and could not be fixed from the publish page.

## Scope

- Publish-page editor and content-review editor: on checklist slides, each drawn item shows its line (title, else
  body, as drawn) and its body in a field marked "not shown on the slide". Field errors attach to the field they name.
- Editing a checklist line sets the title and keeps the body (`clearFields` removed).
- Shared round-trip fixture updated: a line edit keeps the body.

## Non-Goals

- Do not refactor unrelated code
- The backend summary rule is unchanged (owner's choice).

## Acceptance Criteria

- [x] A checklist item shows its line and its body; the body field is labelled as not shown on the slide.
- [x] A `summary_points[i].body` error shows under that item's body field, not the line.
- [x] Typing in the body field sets that item's body in that locale.
- [x] Editing the line sets the title and keeps the body.

## Repro Steps

1. Open the publish page of a carousel whose checklist summary slide has a point with an empty body.
2. The summary error shows under the point's line; no body field exists to fix it.

## Affected Areas

- [ ] Backend
- [x] Frontend
- [x] Tests

## Dependencies

None.

## Progress Log

### 2026-11-09 19:15

Diagnosed from the owner's screenshot and prod slide data. Owner chose to show the body in the editor over relaxing
the rule. Implemented; frontend gates green.

## Files Touched

- `frontend/src/modules/editorial/workspace/lib/checklist-items.ts`
- `frontend/src/modules/editorial/workspace/lib/presentation-slide-resolution.ts`
- `frontend/src/modules/editorial/workspace/components/slide-copy-editor-items.tsx`
- `frontend/src/app/dashboard/create/workspace/phase-review/content-phase-item-text-fields.tsx`
- `frontend/src/modules/editorial/index.ts`
- `frontend/src/i18n/locales/{pt,en}.json`
- `frontend/tests/features/checklist-wysiwyg-editor-ae0543.feature`
- tests: `slide-copy-editor.checklist.test.tsx`, `content-phase-item-text-fields.test.tsx`, `checklist-items.test.ts`
- `backend/tests/fixtures/checklist_edit_roundtrip.json`

## Test Evidence

- Frontend: 844 tests in the editorial module and content review pass; full `frontend:test` gate green.
- Backend `test_checklist_edit_roundtrip.py` passes with the updated fixture.
- Frontend gates run individually, all green (mutation: CI).

## QA Report

Pending (hotfix fast path).

## Blockers

None.
