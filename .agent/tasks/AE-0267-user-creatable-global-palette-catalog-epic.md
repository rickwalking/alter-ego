# AE-0267 — User-creatable global palette catalog (epic)

Status: Ready
Tier: T3
Priority: Medium
Type: Epic
Area: Cross-cutting
Owner: Pedro Marins
Agent Lane: planner → architect → developer → qa → release
Branch: TBD (per child ticket)
Kanban Card: TBD
Created: 2026-06-23
Updated: 2026-06-23

## Goal

Ship a carousel palette **catalog** where curated *root* palettes (typed registry →
`palettes.json`, read-only) coexist with *custom* palettes that any authenticated user
creates, shows, and edits from the frontend. Custom palettes are global and
soft-deletable; image style is derived from light/dark mode; carousels snapshot their
resolved palette at generation so edits never alter past work.

## Problem

After AE-0266, palettes are a closed code-defined set. The product needs runtime,
user-creatable palettes alongside the curated originals — without losing the typed
invariants (light-not-AUTO, light→light-style, brand-lock) or risking the prod DB.

## Scope

- Epic umbrella tracking the phased delivery P1–P4 (children AE-0268..0271).
- See architecture `.agent/reports/AE-0267.arch-plan.md`, ADR
  `docs/decisions/0019-palettes-as-data.md`, planner breakdown
  `docs/plans/ae-0267-palette-catalog-epic.md`.

## Non-Goals

- Per-user/tenant scoping (catalog is global — D2).
- User-chosen image style (derived from mode — D3).
- Editing root palettes (read-only — D1).
- Palette colour-edit history / revert (snapshot makes it non-critical — D9; optional later).

## Acceptance Criteria

- [ ] AE-0268 (P1) merged: `project.theme` is a string reference; prod migration clean.
- [ ] AE-0269 (P2) merged: custom-palette persistence + DB-backed resolver + snapshot.
- [ ] AE-0270 (P3) + AE-0271 (P4) co-deployed: CRUD API + dynamic FE catalog live.
- [ ] All resolved skeptical findings (G1–G8, F1–F3) honoured across children.

## Gherkin Scenarios

Per child ticket (behaviour-changing). The epic itself is a tracking ticket.

## Delta

### ADDED
- `palettes` table; `carousel_projects.theme_snapshot`; palette CRUD API; FE catalog.
### MODIFIED
- `project.theme` enum→string; `resolve_theme` pure→service; FE create page; drift gate.
### REMOVED
- FE hardcoded `CAROUSEL_THEMES`/`THEME_LABEL_KEYS`/`LIGHT_THEME_KEYS` (P4).

## Affected Areas

- Backend: theme model/resolver, palette domain/repo/service
- Frontend: create page, catalog/create-edit UI (impeccable-designed)
- Database: `theme` column type, `palettes` table, `theme_snapshot` column
- API: `/palettes` CRUD
- Tests: resolver, CRUD, migration, FE catalog, drift gate
- Docs: ADR-0019, arch-plan, epic plan
- Deployment: P1 prod migration (isolated); P3+P4 co-deploy behind a flag

## Dependencies

- Blocks: —
- Blocked by: —
- Related: AE-0266 (registry SSOT, supersedes its Phase 4); ADR-0018, ADR-0019

## Implementation Plan

P1 (AE-0268) alone → P2 (AE-0269) → P3 (AE-0270) + P4 (AE-0271) co-deploy.

## QA Checklist

- [ ] Security reviewed (per child, esp. AE-0270)
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-23

Epic created from planner breakdown. Architecture + ADR + two skeptical reviews done.

## Files Touched

Pending (per child).

## Test Evidence

Pending.

## QA Report

Pending.

## Decision Log

D1–D9 + O3 resolved (see `docs/plans/ae-0267-palette-catalog-epic.md`). Two cold-critic
passes (gemini-2.5-pro, glm-5.2) resolved; snapshot-at-generation (D9) adopted.

## Blockers

None.

## Final Summary

Pending.
