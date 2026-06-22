# AE-0264 — expand carousel palettes and add the light flat-editorial image preset

Status: In Development
Tier: T2
Priority: Medium
Type: Feature
Area: backend, frontend
Owner: Pedro Marins
Agent Lane: developer → qa → release
Branch: feat/carousel-palettes-light-editorial
Kanban Card: TBD
Created: 2026-06-22
Updated: 2026-06-22

## Goal

Broaden the carousel image visual range beyond the single dark-neon/cyberpunk
look: add 8 new selectable palettes (5 dark variants + 3 light/editorial) and a
matching **light** image strategy (`flat_editorial`) so the light palettes render
correctly instead of fighting the dark "neon glow" presets. GPT (`openai`) +
`neo_anime` is already the shipped default and is unchanged.

Spec: `docs/design/carousel-image-theme-alternatives.md`
Draft swatch board (approved by the user): `docs/design/carousel-palette-swatches.draft.html`

## Problem

`CAROUSEL_THEMES` shipped only 5 dark palettes and every image strategy phrased a
dark "neon glow" background (`_palette_fragment`). There was no light/editorial
option, and a light palette routed through a dark strategy produces a
contradictory prompt ("Dark background (#f7f5f0)…").

## Scope

- Add 5 dark-variant palettes (plasma_magenta, acid_lime, mono_indigo,
  ember_crimson, blueprint) + 3 light palettes (risograph, paper_editorial,
  clinical_mint) to `CAROUSEL_THEMES` + the `CarouselTheme` enum.
- Add `OpenAIFlatEditorialStrategy` + `IMAGE_STYLE_FLAT_EDITORIAL` + the
  `(openai, flat_editorial)` combo (registry + `SUPPORTED_IMAGE_COMBOS`), with a
  light-aware `_editorial_palette_fragment` (no neon glow).
- Decouple the AUTO rotation pool (`AUTO_ROTATION_THEME_KEYS`) from the full
  palette catalog so AUTO never hands a LIGHT palette to a dark strategy.
- Frontend: expose the new themes + the flat_editorial preset in
  `constants/create.ts`, the zod schema, and en/pt i18n.
- Split the large keyword maps into `carousel_theme_keywords.py` to keep
  `carousel_themes.py` under the 400-line ceiling.

## Non-Goals

- No change to the default combo (still `openai` + `neo_anime`).
- The runtime **AI-auto custom palette** path (LLM-generated `{primary, accent,
  background}` per carousel) is a follow-up increment, not this ticket.
- No change to persona/voice or text content. No backdrop/custom-details
  plumbing (that is AE-0263).

## Classification (no-`.feature`? No — behavior-changing)

Behavior-changing (new user-selectable themes + a new image style). `.feature`
scenarios added to `tests/features/image_generation_provider.feature`.

## Acceptance Criteria

- [x] 13 palettes total; every `CAROUSEL_THEMES` key has a matching
      `CarouselTheme` enum value.
- [x] `(openai, flat_editorial)` resolves to `OpenAIFlatEditorialStrategy`; its
      prompt carries "Flat editorial vector illustration" + "Light background" and
      no "neon glow".
- [x] AUTO never returns a light palette (asserted across 200 unmatched topics).
- [x] Light palettes are reachable only by explicit `project.theme`.
- [x] Frontend selectors + zod schema + en/pt i18n carry the new themes/preset.
- [x] `.feature` updated; backend ruff/mypy/lint-imports/arch-ratchet green;
      frontend lint/typecheck/schema-drift green; full backend + frontend suites green.

## Affected Areas

- Backend: `domain/constants/carousel_themes.py`, new
  `domain/constants/carousel_theme_keywords.py`, `domain/constants/carousel.py`,
  `domain/constants/__init__.py`, `domain/models/carousel.py`,
  `application/services/image_style_strategies.py`,
  `application/services/image_provider_registry.py`,
  `application/services/carousel/theme_resolver.py`
- Backend tests: `tests/unit/application/test_theme_resolver.py`,
  `test_image_provider_registry.py`, `test_image_style_strategies.py`,
  `tests/features/image_generation_provider.feature`
- Frontend: `src/constants/create.ts`, `src/schemas/carousel.ts`,
  `src/i18n/locales/{en,pt}.json`

## QA Checklist

- [ ] Security reviewed (no new external input paths; theme stays `String(30)`)
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested (AUTO never light; explicit light; missing palette keys)
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-22

Implemented end-to-end on `feat/carousel-palettes-light-editorial` (branched off
`origin/main` @ fe0b9ef2). User approved the draft swatch board and asked to build
all 8 palettes + the light editorial preset; GPT neo-anime confirmed as the
existing default. Gate runs pending capture.

## Test Evidence

Pending GATES_JSON capture.

## QA Report

Pending.

## Final Summary

Pending.
