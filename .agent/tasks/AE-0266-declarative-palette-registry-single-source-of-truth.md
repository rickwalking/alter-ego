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
- **Phase 2:** consolidate the two image-strategy maps (`image_provider_registry` +
  `image_prompt_package._STRATEGY_MAP`) into one; add `image_style` to descriptors.
- **Phase 3:** emit `docs/contracts/palettes.json`; add a frontend `palette-drift`
  contract gate; drive `create.ts` options + i18n labels from it.
- **Phase 4 (optional):** runtime `GET /api/carousels/palettes`; FE dynamic catalog.

## Acceptance Criteria

- [x] Phase 1: all 6 derived constants byte-equal their pre-refactor values
      (parity-verified); `resolve_theme` + all callers unchanged.
- [x] Adding a palette = one `PALETTE_REGISTRY` row; brand keywords co-located.
- [x] `__post_init__` makes a light AUTO palette unrepresentable; contract test guards
      enum↔registry drift.
- [x] backend ruff/mypy/lint-imports/arch-ratchet/dead-code green; full unit suite green.
- [ ] Phase 2-4 (follow-up).

## Affected Areas

- Backend: `domain/constants/palette_types.py` (new), `domain/constants/carousel_themes.py`
- Tests: `tests/unit/domain/test_palette_registry.py`

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

## Test Evidence

Phase 1: generator asserts derived == current for all 6 constants before writing;
`test_palette_registry.py` (6) + `test_theme_resolver.py` + `test_image_prompt_package.py`
green; full unit suite 1947 passed / 1 skipped; ruff/mypy/lint-imports/arch-ratchet/vulture green.

## QA Report

Pending.

## Final Summary

Pending (Phase 1 done; ticket stays open for Phases 2-4).
