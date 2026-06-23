# AE-0266 — declarative palette registry (single source of truth for carousel themes)

Status: In Development
Tier: T2
Priority: Medium
Type: Refactor
Area: backend, frontend
Owner: Pedro Marins
Agent Lane: architect → developer → qa → release
Branch: feat/carousel-palettes-light-editorial
Kanban Card: TBD
Created: 2026-06-23
Updated: 2026-06-23

## Goal

Replace the 6+ parallel theme/brand/palette structures with one declarative
`PALETTE_REGISTRY` of frozen `PaletteDescriptor` rows, from which the legacy lookup
maps/sets and the enum guard are derived — so adding a color is one row and the
views can never desync. Brand keywords live co-located with their palette.

Plan: `.agent/reports/AE-0266.arch-plan.md` · ADR: `docs/decisions/0018-declarative-palette-registry.md`.

## Problem

Theme/brand/palette config was 6+ parallel structures (`CAROUSEL_THEMES`,
`BRAND_PALETTES`, `BRAND_KEYWORDS`, `THEME_CATEGORY_KEYWORDS`,
`AUTO_ROTATION_THEME_KEYS`, `LIGHT_THEME_KEYS`) plus a hand-kept `CarouselTheme` enum,
two image-strategy maps, and a frontend mirror. "A palette" was an emergent join across
them, so adding one color meant editing ~8 places and any could silently desync —
three production bugs in one delivery traced to this (light-on-dark AUTO, drifted
strategy maps, FE dropdown missing themes).

## Non-Goals

- No public/user-visible behavior change (derived constants keep exact names + values).
- Not the new palettes/presets themselves (AE-0264) nor the light renderer (AE-0265).
- Phase 1 does **not** move image-style pairing or labels into descriptors (Phases 2-3).
- No external YAML config (kept typed in-code to preserve mypy-strict).

## Classification (no-`.feature`? Yes — pure refactor)

No public/user-visible behavior change: the derived constants keep the exact same
names and values (parity-verified in the generator + a derived-views test), and
`resolve_theme` is untouched. CI/refactor path → focused unit tests + the
enum↔registry drift guard substitute for a `.feature`. Affected gates: backend
lint/type/imports/arch-ratchet/dead-code/test. Reviewer/QA sign-off on the
no-`.feature` classification pending.

## Scope

- **Phase 1 (done):** `domain/constants/palette_types.py` (Palette, PaletteDescriptor,
  PaletteMode, PaletteKind value objects); rewrite `carousel_themes.py` as
  `PALETTE_REGISTRY` + derivations (same public constants); `__post_init__` rejects a
  light palette in the AUTO pool; `tests/unit/domain/test_palette_registry.py` guards
  enum↔registry drift + derived-view consistency.
- **Phase 2 (done):** consolidate the two image-strategy maps (`image_provider_registry` +
  `image_prompt_package._STRATEGY_MAP`) into one `IMAGE_STRATEGY_REGISTRY`. (`image_style`
  on descriptors was intentionally NOT added — see the Phase 2 progress-log decision.)
- **Phase 3 (done):** emit `docs/contracts/palettes.json`; add a frontend `palette-drift`
  contract gate; labels (`label_en`/`label_pt`) become the SSOT for the i18n theme labels.
- **Phase 4 (optional):** runtime `GET /api/carousels/palettes`; FE dynamic catalog.

## Acceptance Criteria

- [x] Phase 1: all 6 derived constants byte-equal their pre-refactor values
      (parity-verified); `resolve_theme` + all callers unchanged.
- [x] Adding a palette = one `PALETTE_REGISTRY` row; brand keywords co-located.
- [x] `__post_init__` makes a light AUTO palette unrepresentable; contract test guards
      enum↔registry drift.
- [x] backend ruff/mypy/lint-imports/arch-ratchet/dead-code green; full unit suite green.
- [x] Phase 2: the two image-strategy maps (`image_prompt_package._STRATEGY_MAP` +
      `image_provider_registry._providers`) fold into one `IMAGE_STRATEGY_REGISTRY`
      (in `image_style_strategies.py`); both call sites consume it; contract test
      asserts registry keys == `SUPPORTED_IMAGE_COMBOS` and both consumers resolve
      the same strategy per combo. Pure refactor — strategy resolution byte-identical.
- [x] Phase 3: `label_en`/`label_pt` added to `PaletteDescriptor` (populated for the
      13 user-selectable themes); `export_palettes.py` emits `docs/contracts/palettes.json`
      from `PALETTE_REGISTRY` + `IMAGE_STRATEGY_REGISTRY`; a backend staleness test +
      `--check` guard the artifact; the frontend `lint:palette-drift` gate (BLOCKING, in
      the `lint` chain) diffs `create.ts` theme keys / `IMAGE_PRESETS` combos /
      `LIGHT_THEME_KEYS` + the en/pt i18n labels against the contract; a rule-fires
      test seeds 5 drift variants and asserts non-zero exit (AE-0180).
- [ ] Phase 4 (optional follow-up).

## Affected Areas

- Backend: `domain/constants/palette_types.py` (new), `domain/constants/carousel_themes.py`
- Phase 2: `application/services/image_style_strategies.py` (registry SSOT),
  `application/services/image_provider_registry.py`,
  `application/services/carousel/image_prompt_package.py`
- Phase 3: `application/services/carousel/palette_contract.py` (new),
  `scripts/export_palettes.py` (new), `docs/contracts/palettes.json` (new artifact),
  `frontend/scripts/check-palette-drift.mjs` (new gate), `frontend/package.json`
  (`lint:palette-drift` in the `lint` chain)
- Tests: `tests/unit/domain/test_palette_registry.py`,
  `tests/unit/application/test_image_strategy_registry.py` (new),
  `tests/unit/application/test_image_prompt_package.py`,
  `tests/unit/application/test_palette_contract.py` (new),
  `frontend/src/scripts/palette-drift.test.ts` (new rule-fires),
  `frontend/tests/features/palette-drift-gate.feature` (new)

## QA Checklist

- [ ] Security reviewed (pure data/typing, no input)
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated (Phase 1)
- [ ] Edge cases (light/auto invariant; enum drift)
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-23

Architect plan + ADR-0018. Phase 1 implemented (commit 7e82e73c): registry +
derivations, parity-verified, 1947 unit tests green. Phases 2-4 are follow-ups.

Phase 2 implemented: consolidated the two parallel `(model, style) → strategy`
maps into one `IMAGE_STRATEGY_REGISTRY` co-located with the strategy classes in
`image_style_strategies.py`. The prompt renderer and the provider registry both
read it, so the AE-0264 drift class (a light palette falling back to the dark
"neon glow" default because the maps disagreed) is now structurally impossible.
The provider registry builds `_providers` by iterating the registry and pairing
each strategy with its model's service. A new contract test pins the SSOT.

**Decision — `image_style` NOT added to `PaletteDescriptor` (deviation from the
plan's Phase 2 bullet):** the palette→style relation is many-to-one only for the
3 *light* palettes (all → `flat_editorial`); the 11 *dark* palettes each pair
with any of 4 dark styles chosen by the user, so there is no single `image_style`
per dark descriptor. Encoding one would be misleading data with no real consumer
(style still comes from `project.image_style`). Deferred to the Phase 3 frontend
contract work, where the light→`flat_editorial` nudge is the actual coupling.

Phase 3 implemented: added `label_en`/`label_pt` to `PaletteDescriptor` (the
single source for the FE dropdown labels) and populated the 13 user-selectable
themes. New `palette_contract.py` projects `PALETTE_REGISTRY` (themes + labels +
light keys) and `IMAGE_STRATEGY_REGISTRY` (preset combos) into a serializable
dict; `export_palettes.py` writes/`--check`s the committed
`docs/contracts/palettes.json`. New frontend `check-palette-drift.mjs` (BLOCKING,
added to the `npm run lint` chain) statically parses `create.ts`
(CAROUSEL_THEMES / THEME_LABEL_KEYS / LIGHT_THEME_KEYS / IMAGE_PRESETS) + the
en/pt locales and fails on any desync from the contract; `auto` is the one
sanctioned FE-only sentinel. A backend staleness test + the AE-0180 rule-fires
test (`palette-drift.test.ts`, 5 seeded violations) guard both ends. The FE was
already in sync, so the gate is blocking from day one (no pre-existing drift to
ratchet, unlike schema-drift).

## Test Evidence

Phase 1: generator asserts derived == current for all 6 constants before writing;
`test_palette_registry.py` (6) + `test_theme_resolver.py` + `test_image_prompt_package.py`
green; full unit suite 1947 passed / 1 skipped; ruff/mypy/lint-imports/arch-ratchet/vulture green.

Phase 2: `test_image_strategy_registry.py` (4 new) + `test_image_prompt_package.py`
+ `test_image_provider_registry.py` + `test_image_provider_ports.py` (40 together)
green; full unit suite **1951 passed / 1 skipped**; backend static gates 15/15 PASS
(format, lint, lint-diff, blanket-ignore, strict-diff, type, imports, arch-ratchet,
docstrings, dead-code, inline-prompts, bandit, pip-audit, integrity, mutation).

Phase 3: `export_palettes.py --check` clean; `test_palette_contract.py` (6 new,
incl. the committed-artifact staleness guard) green; full backend unit suite
**1957 passed / 1 skipped**; backend ruff/format/mypy (522 files) green. Frontend:
`lint:palette-drift` OK against the real tree; `palette-drift.test.ts` **6/6**
(1 pass-through + 5 seeded-drift exit-non-zero); full `npm run lint` exit 0 (no new
jscpd clones); `npm run typecheck` clean; `lint:i18n` OK; backend+frontend integrity
(anti-gaming) PASS; frontend dead-code 0-new.

## QA Report

Pending.

## Final Summary

Pending (Phase 1 done; ticket stays open for Phases 2-4).
