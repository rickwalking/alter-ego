# AE-0154 — Frontend: exhaustive business-component re-homing; ratchet component-type-location down

Status: Review
Tier: T2
Priority: High
Type: Task
Area: Frontend
Owner: developer
Agent Lane: planner → architect → developer → qa → release
Branch: feat/phase-8-legacy-removal
Kanban Card: TBD
Created: 2026-06-16
Updated: 2026-06-16

## Goal

Move any remaining domain-named components still in components/atoms|molecules|organisms into their owning module (Phase 7 did the clear-cut ones); keep generic Neon* primitives atomic. Ratchet the component-type-location baseline (57) down toward 0 by moving inline types to colocated types.ts.

## Problem

Phase 7 re-homed the obvious business components (PersonaCard/RubricCard/BlogPostCard/KanbanBoard) but left ambiguous/remaining domain components in the global atomic folders, and 57 inline component/hook types remain grandfathered.

## Scope

Identify remaining domain-owned components in components/* and move them to their module + barrel (with stories/tests); generic Neon* stay. Move inline object-shape types to colocated types.ts and ratchet component-type-location-baseline.json DOWN. Behavior-preserving.

## Non-Goals

- Generic Neon* primitives stay in components/* (not domain-owned).
- No behavior/UI change; type-only + relocation.

## Modularization Alignment (2026-06-16)

Phase 8 of the modularization plan (§Phase 8 "Remove legacy layers and adapters") — the final phase, after
Phases 0-7 merged (PRs #15-#21). Removes the temporary migration scaffolding to zero. Class A (safe cleanup) is
behavior-preserving and holds the existing green gates with down-only ratchets; Class B (auto-publish cutover +
destructive column drop) is consent-gated + drain-gated (ADR-0008). See `docs/plans/phase-8-legacy-removal.md`.

## Acceptance Criteria

- [x] Remaining domain components SHALL live in their owning module behind the barrel; generic Neon* stay atomic
- [x] component-type-location baseline SHALL ratchet DOWN (toward 0); 0 new — reached **0** (57 → 0)
- [x] typecheck + lint + 822 tests + build + build-storybook green; boundary 0

## Gherkin Scenarios

Not applicable — legacy-removal cleanup; verified by the green-gate safety net (back-end gates.sh + check-integrity + arch-ratchet; front-end typecheck/lint/boundaries/url/circular/tests/build).

## Dependencies

- Blocks: —
- Blocked by: AE-0153
- Related: AE-0152

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-16

Ticket created by planner (Phase 8 breakdown).

## Files Touched

- **Part A (type ratchet):** 57 inline object-shape declarations moved out of component/hook files under `src/modules/**` into **17 new colocated `types.ts`** files (conversation/hooks; editorial-operations analytics/hooks + board {blog-posts,calendar,workflow}/components; editorial workflow {components,hooks} + workspace {components,hooks}; persona/components; publishing/blog {components, listing, public-post, hooks} + distribution {components,hooks}; quality/components). Module barrels + sibling re-exports repointed to the new `types.ts`. `scripts/component-type-location-baseline.json` regenerated (via `npm run component-types:baseline`) to `count: 0`.
- **Part B (re-homing/dead-shim removal):** deleted 4 AE-0140 re-export shims in `src/components/organisms/` (`neon-persona-card`, `neon-rubric-card`, `neon-blog-post-card`, `neon-kanban-board`) whose canonical implementations already live in their modules; removed their entries from `src/components/organisms/index.ts`; repointed the one live importer (`src/app/(public)/blog/page.tsx` → `@/modules/publishing`).
- `frontend/.gitignore` — added `/storybook-static/` (build-storybook output; was untracked and polluting lint).

## Test Evidence

- `npm run typecheck` — clean.
- `npm run lint` — boundary OK (0/0/0 new), URL inventory OK (26), circular OK (0 cycles / 341 modules), **component-type-location OK (0 / ceiling 0 / 0 new)** — the AE-0144 ratchet is fully retired.
- `npm run test` — 75 files, 823 passed.
- `npm run build` — succeeded; `npm run build-storybook` — succeeded.
- `npm run check:legacy` — passed; `npm run test:e2e:auth` — 7 passed.
- `check-integrity.sh frontend` — PASS, 0 blockers / 0 warnings.

## QA Report

Pending (Phase 8 end-of-phase QA on the full branch).

## Decision Log

- **Duplicate "cards" were AE-0140 deferred shims, not true duplicates:** each `components/organisms/neon-*-card` was a re-export shim (marked "removal deferred to Phase 8") over the canonical module implementation. 3 were dead (no importer) → removed; 1 (`neon-blog-post-card`) had a single deep-path importer in `app/(public)/blog` → repointed to the module barrel, then removed. Generic Neon* organisms (sidebar/top-bar/breadcrumb/stats-grid/activity-list/pagination/grid-background/scanline-overlay) left atomic.
- **component-type-location ratcheted all the way to 0:** every grandfathered inline type moved to a colocated `types.ts` (pure move, names/shapes identical), so the ratchet ceiling is now 0 — the Phase 8 exit-gate target for this dimension.
- **`/storybook-static/` gitignored:** `build-storybook` is a documented command + an AC; its output was untracked and broke eslint when present, so it is now ignored.

## Blockers

None.

## Final Summary

Exhaustive component-type-location cleanup: all 57 grandfathered inline component/hook types relocated to colocated `types.ts`, ratcheting the AE-0144 baseline from 57 to **0** (exit-gate target met). Removed the 4 deferred `components/organisms` business-card re-export shims (canonical versions already module-homed; repointed the one live importer). Generic Neon* primitives stay atomic. Behavior-preserving: typecheck, lint (boundary 0 / circular 0 / component-types 0), 823 tests, build, build-storybook, check:legacy, and the AE-0165 auth e2e all green.
