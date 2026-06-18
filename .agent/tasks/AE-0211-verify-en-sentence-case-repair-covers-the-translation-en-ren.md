# AE-0211 — Verify EN sentence-case repair covers the translation_en render source + regression test

Status: Dev Complete
Tier: T1
Priority: Medium
Type: Quality
Area: backend
Owner: Unassigned
Branch: feat/kz-content
Created: 2026-06-18
Updated: 2026-06-18

## Goal

Guarantee EN slide render-source text is sentence-cased; close any gap the existing repair misses.

Source: Kaizen prod sweep `.agent/reports/kaizen-prod-2026-06-18.plan.md` (live carousel run, project b5b61790-9372-4a5a-ae17-30d2df28ef3d), validated by an independent architect cold-critic review.

## Problem

`presentation_validation.py:109 _validate_en_heading_case` (blocking) and `presentation_copy_repair.py:43 _repair_heading_sentence_case_en` already exist — yet prod carousel b5b61790 **still rendered all-lowercase EN headings/bodies** from `carousel_slides.extras.translation_en` (the render source), hot-patched manually 2026-06-18. The repair likely operates on `localized_slides` (proper-cased in the review) but NOT on the `translation_en` field the renderer consumes — a dual-representation gap.

## Scope

- Confirm whether the existing validation/repair covers `extras.translation_en` (the render-source); if not, wire it in.
- Add a regression test: a lowercase EN render-source heading is repaired (or blocked) before render.

## Non-Goals

- Re-implementing the repair (it exists) — only closing the render-source gap.

## Acceptance Criteria

- [x] EN render-source (`translation_en`) headings/bodies are guaranteed sentence-cased before render.
- [x] Regression test fails on a seeded lowercase `translation_en` heading.

## Repro Steps

1. A persisted slide carries `extras.translation_en.heading = "all lowercase en heading"`.
2. The EN export path calls `slides_data_for_language(slides, "en")`, which read the heading/body verbatim from `translation_en` and handed them to `run_design` — no sentence-case repair (the existing repair only touched `localized_slides`).
3. The rendered EN slide showed an all-lowercase heading/body (prod project b5b61790).

## Affected Areas

- [x] Backend
- [ ] Frontend
- [x] Tests

## Dependencies

- Blocks: —
- Blocked by: —
- Related: presentation-policy validation/repair

## Progress Log

### 2026-06-18

- Ticket created.
- Confirmed the gap is REAL: `slides_data_for_language(slides, "en")` in `types.py` reads `translation_en.heading`/`body` verbatim and feeds them to `run_design` (export.py) with no EN sentence-case repair. The existing `deterministic_repair_slide_payload` / `repair_localized_slides` only operate on `localized_slides`, a separate representation — so the render source was never sentence-cased.
- Added an HTML-tag-aware `repair_text_sentence_case_en()` to `presentation_copy_repair.py` and applied it to the EN heading AND body inside `slides_data_for_language` (the point of consumption), guaranteeing the render source is sentence-cased before render. Idempotent for already-cased text.
- Seeded regression tests; verified they fail without the fix and pass with it.

## Files Touched

- `backend/src/rag_backend/application/services/carousel/presentation_copy_repair.py` — add `repair_text_sentence_case_en()` (HTML-tag-aware, idempotent) + export.
- `backend/src/rag_backend/application/services/carousel/types.py` — apply the repair to EN heading/body in `slides_data_for_language`.
- `backend/tests/unit/application/test_bilingual_export.py` — seeded regression tests.

## Test Evidence

```
uv run pytest tests/unit/application/test_bilingual_export.py tests/unit/application/test_presentation_validation.py -q
30 passed
```

Negative control (revert the repair calls) → seeded tests FAIL:
```
test_en_render_source_lowercase_heading_is_sentence_cased FAILED
test_en_render_source_skips_leading_html_tag_when_casing FAILED
```

Gate reproduction:
```
GATES_JSON: {"pass":14,"fail":0,"skip":3,"results":[...]}
```
SKIP=3 (`test`, `diff-cover`, `migrations`) — Postgres-dependent, `DATABASE_URL` unset locally; CI runs them with a live DB service. The AE-0211 unit tests are DB-free and pass via direct pytest.

Integrity (`scripts/ci/check-integrity.sh backend`): 0 net-new blockers, 0 warnings.

## QA Report

Pending.

## Blockers

None.
