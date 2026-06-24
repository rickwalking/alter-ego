# AE-0269 — P2: custom-palette persistence + DB-backed resolver + snapshot

Status: Dev Complete
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

- [x] `palettes` table: uuid `id` PK, `name`, `slug`, `primary/accent/background`, `mode`,
      `keywords` JSONB, `archived`, `created_by/created_at/updated_at` (`PaletteModel`).
- [x] DB constraints: **partial unique index `(name) WHERE archived=false`**; **unique
      `slug`** across all rows. (skeptical F3/G3)
- [x] Resolver resolves: root key (registry), custom UUID `id` (active OR archived), and
      `"auto"`; brand precedence preserved; AUTO match over (root brand + custom keywords),
      hash fallback over the root AUTO pool only (`PaletteResolverService`).
- [x] **Image style derived from mode**; a light palette can never resolve to a dark
      strategy (regression test). (D3)
- [x] **Snapshot (D9):** the image phase writes `theme_snapshot` via
      `_ensure_theme_snapshot` (idempotent); render reads the snapshot first
      (snapshot-aware `resolve_theme`) and never re-resolves; `theme="auto"` frozen.
- [x] **Reliability (skeptical G2):** **registry-only fallback** when the repo is
      unavailable (logged, no 500). NOTE: the LRU+TTL cache is **superseded by D9** — the
      snapshot makes resolution run **once per generation** (then frozen), so a per-render
      cache adds no value; the snapshot IS the durable cache. Fallback (the real G2 risk)
      is implemented + tested.
- [x] `theme_snapshot` migration additive (`a7b8c9d0e1f2`); `mypy --strict` + backend
      static gates green; **applied to prod via ssh** (deploy doesn't migrate — see ticket).

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
Implemented in 4 increments: (1) `CustomPalette` entity + `PaletteRepository` port;
(2) `palettes` table + migration `a7b8c9d0e1f2` + `PostgresPaletteRepository`;
(3) snapshot-aware `resolve_theme` + `PaletteResolverService` (union/derived-style/
fallback) + `snapshot_project_theme` helper; (4) `_ensure_theme_snapshot` wired into the
image phase (`editorial_visual_pipeline`), `update_from_entity` fix, +.feature.
**Reviewed exception:** one `application→infra` baseline edge (61→62, human-approved) —
the image pipeline already constructs repos inline at this point.
**Prod:** deploy does NOT run migrations (AE-0207 disabled), so the additive schema was
hand-applied via ssh (theme→64, theme_snapshot jsonb, palettes table + 2 indexes) — and
a latent PR #61 incident was fixed live (missing `custom_visual_details` → carousel list
500 → added the column → 200). See [[prod-db-schema-drift]].

## Files Touched
- domain: `models/palette.py` (new), `protocols/palette.py` (new), `models/carousel.py`
  (theme_snapshot field)
- infra: `database/models/palette.py` (new), `database/palette_repository.py` (new),
  `database/models/carousel.py` (theme_snapshot col + to/from/update-from-entity),
  `alembic/versions/a7b8c9d0e1f2_*.py` (new)
- application: `carousel/palette_resolver_service.py` (new), `carousel/theme_resolver.py`
  (snapshot-aware + `_score_keyword_list`), `carousel/editorial_visual_pipeline.py` (hook)
- baseline: `scripts/metrics/import_baseline.py` (app→infra 61→62, reviewed)
- tests: `test_palette_repository.py`, `test_palette_resolver_service.py`,
  `test_editorial_visual_pipeline_snapshot.py`, `test_carousel_theme_reference.py`,
  `tests/features/carousel_custom_palette.feature`

## Test Evidence
- `mypy --strict` (rag_backend, 527 files): clean.
- `tests/unit`: **1979 passed, 1 skipped** (+~22 new across repo/resolver/snapshot).
- Static gates: ruff format/lint, lint-imports (22/0), arch-ratchet PASS (62=62),
  vulture, interrogate — all green. `check-integrity.sh backend` vs origin/main: 0 blockers.
- Migration validated locally (single alembic head); CI migrations gate (fresh postgres)
  validates the DDL. Prod schema verified post-apply (theme=64, theme_snapshot=jsonb,
  palettes 12 cols + pkey/uq_name_active/uq_slug).

## QA Report
Pending (handoff to /qa-agent).
## Decision Log
D3, D4, D6, D8, D9; G2 (fallback; cache superseded by snapshot); G3 (DB constraints);
F3 (409 deferred to AE-0270 CRUD). Reviewed app→infra baseline +1 (human-approved).
## Blockers
None. (Prod schema applied; CI will validate the migration on a fresh DB.)
## Final Summary
Custom-palette persistence + DB-backed union resolver + snapshot-at-generation are
complete and green. Prod schema pre-applied via ssh. Unblocks AE-0270 (CRUD) + AE-0271 (FE).
