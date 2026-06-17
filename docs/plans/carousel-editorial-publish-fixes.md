# Carousel Editorial Workflow & Publish Fixes

> Status: Superseded — historical record

## Context

End-to-end editorial carousel runs produced 10 slides instead of the canonical 7, empty publish captions, EN slides without text overlay, broken `/blog/{id}` after site publish, stale create-workspace tabs, missing i18n for publish CTA, and workflow board cards dropping after `published` phase.

## Acceptance Criteria

### AC-1: Seven-slide carousel contract
- Outline generation enforces exactly **7 slides** (intro + optional TLDR on slide 1, summary, 3× content, closing, CTA).
- Image generation and DB persistence never exceed `MAX_SLIDES` (7).
- Project `slides_config` is set to `7_slides`.

### AC-2: Create workspace step history
- Clicking a **completed** step tab shows read-only artifacts for that phase (outline, drafts, images), not the live in-progress panel for the current phase.
- Steps not yet reached show a clear empty state.
- Approve/revise controls only appear when the viewed step matches the active workflow phase gate.

### AC-3: Publish panel copy & i18n
- `create.publishCta` resolves in `en` and `pt` locales.
- Instagram caption and LinkedIn PT/EN fields populate from workflow/project after content finalization.
- Site publish success message includes a working link to `/blog/{projectId}` when the post is public.

### AC-4: Bilingual rendered slides
- After content phase, slides persist EN `translation_en` extras and PT body from drafts.
- After images phase approval, carousel is exported (PT + EN when translations exist), `status=completed`, and `design_tokens` include `rendered_slides_en`.

### AC-5: Public blog URL
- `blog_markdown` is persisted before or during publish so `/blog/{id}` returns 200 for public carousels.
- Publish endpoint still requires `workflow_status=approved_for_publish` and `status=completed`.

### AC-6: Workflow board accuracy
- Kanban includes a **Published** column for `current_phase=published`.
- Cards show `workflow_status` when more informative than `phase_status`.
- Cards link to `CREATE_WORKSPACE` for the project id (unchanged, verified).

## Implementation Notes

| Area | Primary files |
|------|----------------|
| Outline cap | `outline_normalize.py`, `ai_agents.py`, `outline_agent.py`, `editorial_workflow_generators.py` |
| Distribution | `editorial_distribution_pack.py`, `phase_artifact_runner.py`, `_sync_project_phase` |
| Export/complete | `editorial_finalize.py`, `editorial_workflow_service.py` |
| Publish/blog | `crud.py` `publish_carousel` |
| Frontend steps | `create-step-history-panel.tsx`, `create-workflow-panel.tsx`, `page.tsx` |
| i18n | `en.json`, `pt.json` |
| Kanban | `workflow_board.py`, `workflow-adapter.ts` |

## Test Plan

- [x] Backend unit: `test_outline_normalize.py`, `test_editorial_distribution_pack.py`, `test_editorial_finalize.py`, `test_workflow_board.py`
- [x] Integration: `test_phase3_workflow.py` asserts `published` column
- [x] Frontend unit: `step-ids.test.ts`, `workflow-adapter.test.ts` (`workflow_status` preference)
- [x] Frontend unit: `create-step-history-panel.test.tsx`, `merge-publish-project.test.ts`
- [x] Gherkin: `tests/features/carousel_editorial_publish_fixes.feature`
- [x] Workflow API exposes `linkedin_post_pt` / `linkedin_post_en` on state response
- Run `uv run pytest` / `npm test` / `npm run typecheck` on touched packages
