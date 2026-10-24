# AE-0543 — Checklist slide editor edits the text the slide shows (WYSIWYG) + one-off repair

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
PT and EN. Pedro's edits to carousel 5350e0ca slide 8 (summary, save checklist) show on the slide.

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
- One-off repair script `rag_backend.scripts.repair_checklist_items --project <id> [--dry-run|--apply]`. For each
  checklist slide item (PT and EN) whose non-empty body differs from its title it sets the title to the body and
  clears the body. `--apply` writes through `CarouselSlideEditService` (the `PATCH /api/carousels/{id}/slides`
  service: advisory lock, CAS, projection, `needs_republish`, checkpoint patch), then runs
  `republish_completed_carousel` and clears the marker on success. Idempotent.

## Non-Goals

- Changing the checklist template or any slide design.
- Running the repair on prod (Pedro runs it for 5350e0ca after the deploy).

## Acceptance Criteria

- [x] The workflow state lists the checklist slides (POV save slide; `save_checklist` decks' summary/closing; none otherwise).
- [x] On a checklist slide the editor shows each item's displayed line (title, else body), PT and EN, on the publish page and at content review.
- [x] Editing a checklist line sets the title and clears the body; the slide HTML renders the edited text (PT and EN).
- [x] Grid/list slides edit both title and body.
- [x] Repair script: `--dry-run` lists the moves and writes nothing; `--apply` edits through the PATCH service and republishes; a second run finds nothing.

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
  `application/services/carousel/checklist_item_repair.py`, `bootstrap/carousel_checklist_repair.py`,
  `scripts/repair_checklist_items.py`; `docs/architecture/openapi.json`
- frontend: `modules/editorial/workspace/lib/checklist-items.ts`, `lib/presentation-slide-resolution.ts`,
  `components/slide-copy-editor-items.tsx`, `components/types.ts`, `types-ai.ts`, `hooks/types.ts`,
  `hooks/use-editorial-workflow-utils.ts`, `modules/editorial/index.ts`,
  `app/dashboard/create/workspace/phase-review/content-phase-item-text-fields.tsx`,
  `content-phase-structured-fields.tsx`, `content-phase-item-buttons.tsx`, `i18n/locales/{en,pt}.json`
- tests: `backend/tests/features/carousel_checklist_wysiwyg.feature`, `tests/unit/application/test_checklist_wysiwyg.py`,
  `test_checklist_item_repair.py`, `tests/unit/scripts/test_repair_checklist_items_ae0543.py`;
  `frontend/tests/features/checklist-wysiwyg-editor-ae0543.feature`, `checklist-items.test.ts`,
  `slide-copy-editor.checklist.test.tsx`, `content-phase-item-text-fields.test.tsx`

## Test Evidence

Gates on 09b76cb7c (Postgres-backed backend): backend --changed-only 22 PASS 0 FAIL, backend:test 7156 passed,
diff-cover 94%, migrations and schema-drift PASS; frontend --changed-only 15 PASS 0 FAIL, frontend:test 2843 passed,
schema-drift PASS. Mutation: CI. Details in `.agent/reports/AE-0543.dev-summary.md`.

## QA Report

See `.agent/reports/AE-0543.qa.md`.

## Blockers

None.
