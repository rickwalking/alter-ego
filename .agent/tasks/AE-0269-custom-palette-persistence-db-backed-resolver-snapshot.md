# AE-0269 — P2: custom-palette persistence + DB-backed resolver + snapshot

Status: Ready
Tier: T2
Priority: Medium
Type: Feature
Area: backend
Owner: Pedro Marins
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0269-custom-palette-persistence
Kanban Card: TBD
Created: 2026-06-23
Updated: 2026-06-23

## Goal

Persist custom palettes (global `palettes` table + `PaletteRepository`), turn
`resolve_theme` into an application service that resolves over the union of root
(registry) and custom (DB) palettes, and snapshot the resolved palette onto each
carousel at generation so later edits never alter past work. No frontend yet.

## Problem

Custom palettes must live somewhere mutable (DB) and be resolvable alongside roots. The
current `resolve_theme` is a pure function over constants; adding custom palettes forces
a DB dependency on the generation hot path — which must not become a new failure mode.

## Scope

- `palettes` table + DB constraints; `PaletteRepository` port + async adapter.
- `resolve_theme` → application service over registry ∪ DB, with cache + fallback.
- `carousel_projects.theme_snapshot` JSONB; freeze resolved palette at generation.
- Image style derived from mode (light→`flat_editorial`, dark→default) via the shipped
  `IMAGE_STRATEGY_REGISTRY`.

## Non-Goals

- CRUD endpoints / write API (AE-0270).
- Frontend (AE-0271).

## Acceptance Criteria

- [ ] `palettes` table: uuid `id` PK, `name`, `slug`, `primary/accent/background`, `mode`,
      `keywords` JSONB, `archived`, `created_by/created_at/updated_at`.
- [ ] DB constraints: **partial unique index `(name) WHERE archived=false`**; **unique
      `slug`** across all rows. (skeptical F3/G3)
- [ ] Resolver resolves: root key (registry), custom UUID `id` (active OR archived), and
      `"auto"`; brand precedence preserved; AUTO match over (root brand ∪ custom keywords),
      hash fallback over the root AUTO pool only.
- [ ] **Image style derived from mode**; a light palette can never resolve to a dark
      strategy (regression test). (D3)
- [ ] **Snapshot (D9):** generation writes `theme_snapshot`
      (`{primary,accent,background,mode,resolved_ref,resolved_at}`); render/regeneration
      read the snapshot and never re-resolve; `theme="auto"` frozen at first generation.
- [ ] **Reliability (skeptical G2):** in-process LRU+TTL cache (invalidated on write);
      **registry-only fallback** when the repo is unavailable (logged + metric, no 500);
      resolver-latency metric emitted.
- [ ] `theme_snapshot` migration additive + reversible; `mypy --strict` + full gates green.

## Gherkin Scenarios

```gherkin
Feature: Custom palettes resolve and snapshot at generation

  Scenario: A carousel snapshots its resolved palette
    Given a custom dark palette "Aurora" exists
    And a project references it and is generated
    When the palette "Aurora" is later edited to new colours
    Then the already-generated carousel still renders the original colours

  Scenario: Light custom palette never gets a dark image strategy
    Given a custom palette with mode "light"
    When its image style is derived
    Then it is "flat_editorial" and never a dark neon strategy

  Scenario: Resolver degrades safely when the palette repo is down
    Given the PaletteRepository is unavailable
    When a project with a root-key theme is generated
    Then resolution falls back to the registry, logs, and does not error

  Scenario: AUTO is frozen at generation
    Given a project with theme "auto" generated today resolving to palette X
    When a new custom palette with overlapping keywords is created tomorrow
    And the project is regenerated
    Then it still renders palette X from its snapshot
```

## Delta

### ADDED
- `palettes` table + repo (port + adapter); `theme_snapshot` column; resolver cache/fallback.
### MODIFIED
- `theme_resolver.py` pure→service; generation writes the snapshot.
### REMOVED
- (none)

## Affected Areas

- Backend: palette domain/repo/service, resolver, generation snapshot
- Database: `palettes` table, `theme_snapshot` column
- Tests: resolver paths, snapshot stability, derived-style regression, degraded mode
- Observability: resolver-latency + fallback metrics

## Dependencies

- Blocks: AE-0270, AE-0271
- Blocked by: AE-0268
- Related: AE-0267 (epic), ADR-0019

## Implementation Plan

1. Table + migration + repo. 2. Resolver service + cache/fallback. 3. Snapshot at
generation. 4. Derived-style + degraded-mode tests.

## QA Checklist

- [ ] Security reviewed (no external input yet; DB constraints)
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested (archived resolve, repo down, auto freeze)
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-23
Created from AE-0267 planner breakdown.

## Files Touched
Pending.
## Test Evidence
Pending.
## QA Report
Pending.
## Decision Log
D3, D4, D6, D8, D9; G2/G3 resolutions — see arch-plan.
## Blockers
None.
## Final Summary
Pending.
