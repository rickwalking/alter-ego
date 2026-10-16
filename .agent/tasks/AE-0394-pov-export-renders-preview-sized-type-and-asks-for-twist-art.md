# AE-0394 — POV export renders preview-sized type and asks for twist artwork

Status: In Development
Tier: T1
Priority: P0
Type: Bug
Area: backend
Owner: Claude (owner-requested manual hotfix, polished with /impeccable)
Agent Lane: developer → qa → release
Branch: fix/ae-0394-pov-render-scale
Kanban Card: TBD
Created: 2026-10-16
Updated: 2026-10-16

## Goal

Make "Ponto de Vista" carousels export as publishable Instagram slides, and stop 9-slide POV exports from failing on a missing twist image.

## Problem

The first end-to-end POV carousel (project 64f13017, 2026-10-16) showed two render bugs:

1. **Preview-sized type on the export canvas.** The exporter scales the standard slide classes for 1080x1350 (and 2160x2700) through its CSS injection. The POV classes from AE-0376 (`.pov-hook-*`, `.pov-statement-*`, `.pov-check-*`, `.pov-cta-*`, `.pov-footer`) were never part of it. Slides 1, 2, 3, 8 and 9 exported 34px type on a 1080px canvas, and the slide-1 photo sat in a 58% box.
2. **Twist artwork that never exists.** The twist role used `insight_quote`. The POV contract never fills `insight`, so the strategy always fell back to the full-artwork hero layout and referenced `images/slide_7.jpg`. The images phase correctly generates no art for the twist (`image_required: false`), so the export preflight failed with `image_decode_timeout`.

## Scope

- `infrastructure/external/playwright_export_pov.py` (new): POV export rules for the standard and HD canvas (HD doubles every px), injected by the exporter after its base overrides.
- `css/slide_styles_pov.py`: the slide-1 photo is full-bleed (`object-fit: cover`) with a top scrim from `var(--bg)`, so the hook reads in the photo's negative space (app preview and export).
- `role_layouts.py`: the twist role uses the statement layout (no artwork), matching the contract.

## Non-Goals

- Radar IA layouts (unchanged; their export overrides already exist).
- Content-phase LLM failures from the same run (separate ticket).

## Acceptance Criteria

- [x] AC1: On the export canvas, POV statement headings are 84px, bodies 36px and the hook 92px; HD doubles every size.
- [x] AC2: The exporter injects the POV rules after the base overrides (standard and HD).
- [x] AC3: Slide 1 shows the owner's photo full-bleed with a top scrim.
- [x] AC4: A 9-slide POV deck renders the twist (slide 7) with the statement layout and no image reference.

## Gherkin Scenarios

`backend/tests/features/carousel_pov_layouts.feature`:
- "Layout by role" (updated: slide 7 is statement)
- "The twist slide renders without artwork"
- "POV slides scale for the export canvas"
- "The exporter applies the POV rules"
- "Slide 1 shows the owner's photo full-bleed"

## Delta

### ADDED

- `backend/src/rag_backend/infrastructure/external/playwright_export_pov.py`
- `backend/tests/unit/infrastructure/test_playwright_export_pov_ae0394.py`

### MODIFIED

- `playwright_export.py` (one extra `page.evaluate`)
- `slide_styles_pov.py` (full-bleed hook photo + scrim)
- `role_layouts.py` (twist → statement)
- `test_pov_layouts_ae0376.py`, `test_playwright_export.py`, `carousel_pov_layouts.feature`

### REMOVED

- `INSIGHT_QUOTE_STRATEGY` constant from `role_layouts.py` (no other users; the `insight_quote` strategy itself stays in the registry).

## Affected Areas

- Backend: carousel template CSS, exporter
- Frontend: none
- Database: none
- API: none
- Tests: unit + feature
- Docs: this ticket
- Prompts/LLM: none
- Observability: none
- Deployment: none

## Dependencies

- Blocks: publishing the first POV carousel (64f13017)
- Blocked by: none
- Related: AE-0376 (POV layouts), AE-0371

## Implementation Plan

1. Reproduce with the prod HTML and the exporter's exact viewport and injection (local Playwright harness).
2. Add the POV export rules (standard + HD) and inject them.
3. Make the slide-1 photo full-bleed with a scrim.
4. Map the twist role to the statement layout.
5. Tests + feature scenarios; verify with renders at both scales.

## QA Checklist

- [x] Security reviewed (CSS only; injected CSS is escaped into a JS template literal)
- [x] Code quality reviewed
- [x] Acceptance criteria validated
- [x] Edge cases tested (max-length heading/hook copy budgets fit; HD scale)
- [x] Orphan/unfinished code checked

## Progress Log

### 2026-10-16 03:10

Reproduced locally with the prod HTML, fixed, and verified renders at 1080x1350 and 2160x2700. Negative control: with the old twist mapping, 2 tests fail.

## Files Touched

See Delta.

## Test Evidence

- AE-0394 + exporter + POV layout tests: 46 passed.
- Negative control (old twist mapping): 2 failed.
- Static gates (changed-only): GATES_JSON {"pass":17,"fail":0,"skip":5} (DB gates and mutation run in CI).

## QA Report

Pending (hotfix fast path: CI Test & Coverage decides).

## Decision Log

- 2026-10-16: The twist uses the statement layout, not insight_quote: the contract has no insight field and no twist artwork.

## Blockers

None.

## Final Summary

The POV export now scales for the 1080/2160 canvas, slide 1 is a full-bleed photo, and the twist renders without artwork.
