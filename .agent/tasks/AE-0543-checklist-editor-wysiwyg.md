# AE-0543 — Checklist slide editor edits the text the slide shows (WYSIWYG)

Status: Review
Tier: T1
Priority: High
Type: Bug
Area: Fullstack
Owner: Claude Code (claude-opus-5-5)
Branch: fix/ae-0543-checklist-wysiwyg
Created: 2026-10-23
Updated: 2026-10-24

## Goal

What the slide editor shows for a structured item is exactly what the slide renders, before and after an edit, in
PT and EN, so an edit to a checklist slide (carousel 5350e0ca slide 8: summary, save checklist) shows on the slide.

## Problem

The checklist template (`save_checklist.py`) renders one line per item: `title`, else `body`. The editor
(`StructuredItemsEditor`) edited only `body`, so on a generated item (title and body both set) an edit was saved
but never shown. Grid and list layouts (`summary_grid`, `feature_grid`, `numbered_list`) render title and body,
but the publish-page editor exposed only the body, so the title on the slide could not be edited there.

## Decision

Pedro: WYSIWYG. For checklist items the editor edits exactly the text the slide shows. The template stays as is
(changing it would change the design of existing slides); the editor follows the layout instead.

## Scope

- Backend: `GET .../workflow` returns `checklist_slide_indexes`, the slides that render their items as checklist
  lines. It is computed by the same rule the renderer uses (`checklist_slide_numbers` in `role_layouts.py`: the POV
  save role, or a deck whose chosen layout is `save_checklist`, for summary and closing slides).
- Frontend: `resolveLocalizedSlides` marks those slides `checklist`. On a checklist slide, the publish-page editor
  and the content review show one "Checklist line" per item with the displayed text (title, else body); an edit
  writes `title` and empties `body` in the same update. Other slides show the title and the body, both editable.
- The editor offers what the template draws: list order summary_points, actions, features on both sides; on a
  checklist slide the publish-page editor offers the first list with a line, blank items dropped, at most five lines;
  the content review edits that list and keeps empty slots (how a line is added).
- `POST .../workflow/start` computes `checklist_slide_indexes` too, so a start response never wipes the list.

## Non-Goals

- Changing the checklist template or any slide design.
- A data repair: the one-off repair script was removed in review (it would also have overwritten generated lines,
  whose hidden body differs from the title); carousel 5350e0ca was already repaired on prod.

## Acceptance Criteria

- [x] The workflow state lists the checklist slides (POV save slide; `save_checklist` decks' summary/closing; none otherwise).
- [x] On a checklist slide the editor shows each item's displayed line (title, else body), PT and EN, on the publish page and at content review.
- [x] Editing a checklist line sets the title and clears the body; the slide HTML renders the edited text (PT and EN).
- [x] Grid/list slides edit both title and body.
- [x] The checklist editor offers the lines the slide draws (template list order, blank items dropped, max 5).
- [x] The start response lists the checklist slides; workflow events that do not carry the list keep it.
- [x] End-to-end test: editor edit -> PATCH route -> stored rows -> rendered HTML, PT and EN, from a shared fixture.

## Repro Steps

1. A POV carousel, slide 8 (summary, save checklist), item `{title: "A", body: "B"}`. Edit the item on the publish page.
2. Before: the editor showed and saved `body`; the slide kept showing "A". After: the editor shows "A", and an edit to "C" saves `{title: "C", body: ""}`, which the slide shows.

## Affected Areas

- [x] Backend
- [x] Frontend
- [x] Tests

## Dependencies

None.

## Progress Log

### 2026-10-24 14:00

Review of #276: removed the repair script and its tests; added the editor -> PATCH -> render round trip (shared
fixture), aligned the item-list order and the drawn lines with the template, and made the start route compute the
checklist slides.

### 2026-10-24 01:40

Renumbered from AE-0541 (main merged a different AE-0541 ticket in #272). External QA round 1 WARN: fixed the
conflict reporting, the shared item keys, the supported-type rule and a literal; confirmation round PASS.

### 2026-10-24 00:10

Implemented backend signal, frontend editor, and the repair. Verified the repair end to end on a throwaway local
Postgres (seeded 9-slide carousel): dry run listed 2 moves (PT + EN; equal and empty bodies left alone), apply wrote
the projection through the slide-edit service (lock_version 1 -> 2, `needs_republish` set, audit row in the outbox),
the republish re-rendered slide 8 with the edited text (it then stopped on the seed's missing artwork files, which a
real carousel has), and a second apply found 0 moves. The run caught a bug (the project id must be passed as a string
to `db.get`), fixed before commit.

## Files Touched

- backend: `application/services/carousel_template/role_layouts.py`, `api/schemas/carousel_workflow.py`,
  `api/routes/carousels/editorial_workflow.py`, `api/routes/carousels/editorial_workflow_routes_layouts.py`,
  `api/dependencies/carousel_access.py`; `docs/architecture/openapi.json`
- frontend: `modules/editorial/workspace/lib/checklist-items.ts`, `lib/presentation-slide-resolution.ts`,
  `lib/presentation-review-utils.ts`, `components/slide-copy-editor-items.tsx`, `components/types.ts`, `types-ai.ts`,
  `hooks/types.ts`, `hooks/use-editorial-workflow-utils.ts`, `modules/editorial/index.ts`,
  `app/dashboard/create/workspace/phase-review/content-phase-item-text-fields.tsx`,
  `content-phase-structured-fields.tsx`, `content-phase-item-buttons.tsx`, `content-phase-locale-extras.tsx`,
  `i18n/locales/{en,pt}.json`
- tests: `backend/tests/features/carousel_checklist_wysiwyg.feature`, `tests/fixtures/checklist_edit_roundtrip.json`,
  `tests/unit/application/test_checklist_wysiwyg.py`, `test_checklist_edit_roundtrip.py`,
  `tests/unit/api/test_reload_carousel_project.py`, `tests/integration/test_carousel_workflow_safety_net.py`,
  the two editorial golden snapshots; `frontend/tests/features/checklist-wysiwyg-editor-ae0543.feature`,
  `checklist-items.test.ts`, `checklist-lines.test.ts`, `slide-copy-editor.checklist.test.tsx`,
  `slide-copy-editor.roundtrip.test.tsx`, `use-editorial-workflow-utils.checklist.test.ts`,
  `content-phase-item-text-fields.test.tsx`

## Test Evidence

Gates on 09b76cb7c (Postgres-backed backend): backend --changed-only 22 PASS 0 FAIL, backend:test 7156 passed,
diff-cover 94%, migrations and schema-drift PASS; frontend --changed-only 15 PASS 0 FAIL, frontend:test 2843 passed,
schema-drift PASS. Mutation: CI. Details in `.agent/reports/AE-0543.dev-summary.md`.

## QA Report

See `.agent/reports/AE-0543.qa.md`.

## Blockers

None.
