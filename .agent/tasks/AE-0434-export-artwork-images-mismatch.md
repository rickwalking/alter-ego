# AE-0434 — Final export fails with image_decode_timeout: export expects artwork the images phase never made

Status: Done
Tier: T1
Priority: P1
Type: Bug
Area: Backend
Owner: Claude (orchestrator-reported prod hotfix, 2026-10-19)
Agent Lane: developer → qa → release
Branch: feat/ae-0434-export-artwork-images-mismatch
Kanban Card: TBD
Created: 2026-10-19
Updated: 2026-10-19

## Goal

A carousel export never references artwork the images phase did not plan, and a missing
artwork file fails the preflight with a reason that names the slide.

## Problem

Prod, 2026-10-19, carousel `5344b6c6-1d66-4b0e-9989-93f1316f8829` (`news_analysis`,
`hero_lower_third_v4`, 7 slides, autopilot run `8e484fe5`). At `final_review` the export
raised `PlaywrightExportPreflightError` (`export_preflight_failed`, violation codes
`["image_decode_timeout", "image_decode_timeout"]`) → `background_resume_failed`.
`pt/carousel.html` has `<img src="../images/slide_N.jpg">` for slides 1-6, but `images/`
holds only `slide_1, 3, 4, 5.jpg` (exactly `image_assets`). A send-back to `images`
re-used the same 4 images and generated nothing for slides 2 and 6.

Read-only prod check of the 15 most recent output dirs: POV decks (`pov_hook_v1`)
reference only their generated slides; v1-v3 decks illustrate and reference every
slide 1-6; 5344b6c6 is the first Radar IA v4 deck to reach export.

### Root cause (file:line on `origin/main`, c9aac8162)

- `hero_lower_third_v4.yaml:14-58` is a **role contract**: `image_required: false` for the
  news summary (slide 2), the twist and the verdict; `image_scope.artwork_slides: [1, 3, 4, 5]`.
- The images phase honours it: `nodes/images.py:442` → `filter_image_slides(...,
  artwork_slide_numbers(project))` (`image_artwork.py:17`) plans slides 1, 3, 4, 5 only.
- The renderer does not: `html_template.py:196` only swaps layouts per role for **POV**
  decks (`role_layouts.pov_slide_strategies` returns `{}` for Radar IA), so every
  lower-third strategy (`summary_grid`, `feature_grid`, `hero_content`, …) calls
  `render_lower_third_shell`, and `lower_third_shell.py:26` unconditionally emits
  `images/slide_{N}.jpg`.
- The missing file makes `img.decode()` reject; `playwright_geometry_scripts.py:330-340`
  reports every rejection as `image_decode_timeout`, hiding the real cause.

Not involved: the manual `actions` → `features` key swap on slide 6. The mismatch is
general to every Radar IA v4 deck (slide 2 is always `news`, the verdict and the twist
never have artwork), independent of the closing slide's item key, so that path is
left unchanged.

## Scope

- Renderer uses the same artwork set as the images phase, sized to the rendered deck
  (`role_layouts.deck_artwork_slides`); slides outside it render a gradient-only
  artwork region (`.slide-artwork.slide-artwork-none`, no `<img>`). Fixed contracts
  (v1-v3) unchanged; an explicit cover `artwork_src` (GrokBot, AE-0418) still wins.
- Export preflight: before Playwright launches, every local `.slide-artwork img` must
  exist on disk, else `PlaywrightExportPreflightError("export_preflight_failed:
  slide_artwork_missing: slide_2, slide_6")` with blocking `slide_artwork_missing`
  violations per slide.

## Non-Goals

- Generating artwork for slides the contract says have none (ADR-0021 D8 / v4 contract).
- Changing the decode script's timeout reporting for real decode failures.
- The legacy no-registry renderers in `carousel_template/slides.py` (not used by any
  export path; `apply_design_tokens` discards their HTML). The new preflight still
  guards them.

## Acceptance Criteria

- [x] AC1: a v4 deck with summary + closing slides and images only for 1, 3, 4, 5 renders
  artwork only for 1, 3, 4, 5 and passes the artwork preflight (prod 5344 fixture).
- [x] AC2: for v4 decks of 7 and 8 slides, PT and EN, the slides with artwork in the HTML
  equal the slides the images phase plans.
- [x] AC3: fixed contracts keep artwork on every lower-third slide; an explicit cover wins.
- [x] AC4: a missing artwork file fails the export before Playwright with
  `slide_artwork_missing: slide_N` (not `image_decode_timeout`).
- [ ] AC5: backend gates (except mutation, hotfix fast path) green locally; CI green.

## Gherkin Scenarios

`backend/tests/features/carousel_export_artwork_ae0434.feature`
- Summary and closing slides without images export
- The images phase and the template agree on artwork slides (7/8 slides, PT/EN)
- Fixed contracts keep artwork on every lower-third slide
- An owner-chosen GrokBot cover still renders on a slide without planned artwork
- Remote artwork is not checked on disk
- A missing artwork file fails the preflight with a clear reason
- The missing-artwork check runs before Playwright

## Affected Areas

- [x] Backend
- [ ] Frontend
- [x] Tests

## Dependencies

None.

## Operational recovery for 5344b6c6 (after deploy)

The project is parked at the `images` gate, `awaiting_human` (lock_version 17). Approve
it from the images gate (`POST /api/carousels/5344b6c6-…/workflow/resume`,
`action: "approve"`, the UI "Aprovar" button on the images phase). Approving from
`images` runs `finalize_carousel_after_images_approval`
(`editorial_workflow_service.py:415-424`), which re-renders PT and EN HTML from the
persisted slide rows (`refinement_service.re_render_slides` → `run_design`) with the
fixed renderer, so slides 2 and 6 no longer reference artwork; the 4 existing images
satisfy the preflight and the export completes. No image regeneration is needed. If a
fresh export is ever needed again on a completed deck, the republish action
(`carousel_republish.py`) takes the same path.

## Progress Log

### 2026-10-19

Root cause traced (prod read-only + code), renderer + preflight fix, Gherkin + tests.

## Files Touched

- `backend/src/rag_backend/application/services/carousel_template/{html_template,role_layouts,lower_third_shell}.py`
- `backend/src/rag_backend/application/services/carousel_template/strategies/{intro,hero_content,summary_grid,feature_grid,numbered_list,stat_card_grid,insight_quote}.py`
- `backend/src/rag_backend/application/services/carousel_template/css/slide_styles_shell.py`
- `backend/src/rag_backend/domain/protocols/carousel.py`, `domain/constants/playwright_geometry.py`
- `backend/src/rag_backend/infrastructure/external/{playwright_artwork_check,playwright_export}.py`
- `backend/tests/features/carousel_export_artwork_ae0434.feature`
- `backend/tests/unit/application/test_export_artwork_ae0434.py`
- `backend/tests/unit/infrastructure/test_playwright_artwork_check_ae0434.py`

## Test Evidence

Hotfix fast path (no local mutation; no usable local Postgres: Docker down, no
credentials for the system clusters, so the DB gates run in CI).

- New tests: `test_export_artwork_ae0434.py` (10) + `test_playwright_artwork_check_ae0434.py` (6):
  16 passed; 6 fail on the pre-fix renderer (verified by swapping the old `html_template.py`).
- `uv run pytest tests/unit -p no:randomly`: 4937 passed, 1 skipped.
- Python 3.11 import check (`uv run --python 3.11`): OK.
- `bash scripts/ci/gate-capture.sh backend` (non-DB gates): format, lint, lint-diff,
  blanket-ignore, strict-diff, type, imports, arch-ratchet, docstrings, dead-code,
  inline-prompts, redis-factory, autopilot-env, healthcheck-loopback, bandit, pip-audit,
  integrity = PASS; test, diff-cover, migrations, schema-drift = SKIP (no DATABASE_URL);
  mutation: deferred to CI (hotfix fast path). The group run started mutmut by mistake; it
  was killed after a few minutes, so its FAIL line is the kill, not a result.
- CI: PR #155.

## QA Report

Pending.

## Blockers

None.

## Final Summary

**Merged and closed (orchestrator, 2026-10-20).** Merged #155 (4f3bc3f, 2026-10-19), deployed. Prod: carousel 5344b6c6 images gate approved, export rendered all slides + PDF; published to Instagram 2026-10-20 08:53Z. Follow-up (precise missing-image reason) shipped in AE-0439.
