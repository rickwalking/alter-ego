---
status: accepted
date: 2026-06-23
---

# ADR-0018: Declarative palette registry as the single source of truth for carousel themes

## Context and Problem Statement

Carousel theme/brand/palette config was expressed as 6+ parallel module-level
structures (`CAROUSEL_THEMES`, `BRAND_PALETTES`, `BRAND_KEYWORDS`,
`THEME_CATEGORY_KEYWORDS`, `AUTO_ROTATION_THEME_KEYS`, `LIGHT_THEME_KEYS`) plus a
hand-kept `CarouselTheme` enum, two image-strategy maps, and a frontend mirror
(`create.ts` options + i18n + zod). "A palette" was an emergent join across these,
so adding one color meant editing ~8 places and any of them could silently desync.
Three production bugs in one delivery traced to this: a light palette auto-assigned
to a dark image strategy, a light palette rendered with a dark "neon glow" prompt
(two strategy maps drifted), and the frontend dropdown silently missing new themes.

## Considered Options

- **Builder pattern** — fluent step-wise construction.
- **Declarative registry of frozen descriptors** — one typed row per palette; derive
  the legacy views.
- **External YAML/JSON config + loader.**

## Decision Outcome

Chosen: **a declarative registry of frozen `PaletteDescriptor` value objects**
(`PALETTE_REGISTRY`) as the single source of truth. Every legacy lookup dict/set is
**derived** from it (same public names and values — parity-verified), so callers and
`resolve_theme` are unchanged. Each descriptor carries all of a palette's properties
(colors, light/dark mode, kind, brand/category keywords co-located with the colors,
AUTO eligibility); later phases add the paired image style and display labels.

A **Builder was rejected** as the core mechanism: palettes are flat static value
objects, so a Builder adds a second representation and ceremony without removing any
parallel structure (it may be offered later as optional fluent sugar). **External
YAML was deferred** to preserve mypy-strict typing; the registry can *emit* JSON for
the frontend contract without sourcing from it.

### Consequences

- Good: adding a palette is **one registry row**; brand keywords live next to their
  colors; derived views cannot desync; a `__post_init__` makes "light palette in the
  dark AUTO pool" unrepresentable; a contract test guards enum↔registry drift.
- Good: `carousel_themes.py` shrank 408 → 161 lines.
- Trade-off: the `CarouselTheme` enum stays hand-written (generated enums lose static
  members / IDE ergonomics) — guarded by a CI drift test instead of derived.
- Follow-up (phased, non-breaking): consolidate the two image-strategy maps into one
  registry (Phase 2); emit `palettes.json` + a frontend `palette-drift` contract gate
  (Phase 3); optional runtime palettes endpoint (Phase 4).

## More Information

Plan: `.agent/reports/AE-0266.arch-plan.md`. Phase 1 implemented in the
`feat/carousel-palettes-light-editorial` branch (PR #61). Supersedes the prior
ad-hoc-parallel-constants approach for theme config.
