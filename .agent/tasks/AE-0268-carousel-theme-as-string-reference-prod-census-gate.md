# AE-0268 — P1: carousel theme as string reference (+ prod census gate)

Status: Dev Complete
Tier: T2
Priority: Medium
Type: Refactor
Area: backend
Owner: Pedro Marins
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0268-theme-string-reference
Kanban Card: TBD
Created: 2026-06-23
Updated: 2026-06-23

## Goal

Replace the `CarouselTheme` StrEnum as the type of `CarouselProject.theme` (domain model
and DB column) with a `str` reference (root key | `"auto"` | future custom UUID id). The
enum is retained only as the canonical root-key list. No user-visible behaviour change —
this unblocks custom palettes (which cannot be enum members) and ships alone to isolate
the prod migration.

## Problem

`project.theme: CarouselTheme` is persisted as an enum column and referenced in ~9 source
files. Custom palettes can't be enum members, so the type must become a string reference
before any catalog work. The prod DB has historically drifted from Alembic, so the
migration is the riskiest single step of the epic.

## Scope

- Change `CarouselProject.theme` type to `str`; keep `CarouselTheme` as the root-key list.
- Alembic migration: `theme` enum → string, expand-only/in-place.
- Update all read sites (`theme.value` → direct; `CarouselTheme.X` comparisons → lookups).
- Pre-migration prod census + DDL capture as a blocking gate.

## Non-Goals

- Any custom-palette persistence/resolver/API (AE-0269+).
- Behaviour change to theme resolution (resolver still reads only the registry).

## Acceptance Criteria

- [x] **Pre-migration prod census — DONE (via ssh root@206.189.180.85, 2026-06-23).**
      Prod `carousel_projects.theme` is `character varying(30)` (NOT a PG enum), matching
      the model. Values: `auto`×16, `cybersecurity`×2, `ai_competition`×2, `source_code`×1,
      `social_engineering`×1 — every value is a root key or `"auto"`, all ≤18 chars. No
      drift, no unexpected values → census GREEN, no migration required. (skeptical G4)
- [x] ~~Migration is expand-only/in-place~~ **N/A — no migration needed.** The column is
      already `String(30)` (not a PG enum), so the enum→string change is domain-layer
      only; zero DDL. Confirmed via `infrastructure/database/models/carousel.py:60`.
- [x] ~~Roll-forward recovery / downgrade contingency~~ **N/A** (no migration).
- [x] ~~Staging upgrade/downgrade trial~~ **N/A** (no migration). The prod census above
      is the only remaining prod-side check, and it is read-only/non-mutating.
- [~] Post-deploy **monitoring query** (`SELECT theme … GROUP BY 1`, all values
      resolvable) — provided as an ops check; pairs with the census (owner-run).
- [x] All 10 `CarouselTheme` read sites updated; `mypy --strict` clean (522 files);
      backend static gates green; **1957 existing tests unchanged + 5 new** → "no
      public/user-visible behaviour change" asserted (AE-0153 refactor path). API schema
      was already `str` → no OpenAPI change.

## Gherkin Scenarios

```gherkin
Feature: Carousel theme stored as a string reference (no behaviour change)

  Scenario: Existing enum-valued projects round-trip after migration
    Given a carousel project persisted with theme "plasma_magenta" before the migration
    When the enum->string migration runs
    Then the project's theme reads back as "plasma_magenta"
    And resolve_theme returns the identical palette as before

  Scenario: Migration refuses an unknown legacy value (census gate)
    Given the prod census finds a theme value that is not a root key or "auto"
    Then the migration is not applied until the value is reconciled

  Scenario: A NULL/absent theme survives the convert unchanged
    Given a carousel project row whose theme is NULL
    When the enum->string migration runs
    Then the row's theme remains NULL and the project still resolves to the AUTO default
```

## Delta

### ADDED
- Alembic migration (theme enum→string); prod census + monitoring queries (docs).
### MODIFIED
- `domain/models/carousel.py`, `infrastructure/database/models/carousel.py`,
  `theme_resolver.py`, `api/routes/carousels/crud.py`, `generate_carousel.py`,
  `modules/editorial/*` (theme reads).
### REMOVED
- `CarouselTheme` as the project field/column **type** (kept as root-key list).

## Affected Areas

- Backend: theme model + read sites
- Database: `carousel_projects.theme` column type (enum→string)
- Tests: migration round-trip, resolver unchanged, census assertion
- Deployment: **auto-deploys prod on merge — schedule a calm window**
- Observability: post-deploy monitoring query

## Dependencies

- Blocks: AE-0269
- Blocked by: —
- Related: AE-0267 (epic), ADR-0019

## Implementation Plan

1. Run + attach the prod census + DDL (gate). 2. Write expand-only migration. 3. Update
read sites. 4. Staging trial (upgrade+downgrade from prod backup). 5. Monitoring query.

## QA Checklist

- [ ] Security reviewed (migration only; no new input)
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested (unknown legacy value, null theme)
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-23
Created from AE-0267 planner breakdown. Implemented: changed `CarouselProject.theme`
to `str`, updated all 10 enum-assuming sites, added focused tests. **Key finding:** the
DB column was already `String(30)`, not a PG enum — so NO Alembic migration is required
(the heavy migration ACs are N/A). The UUID-width column widening moves to AE-0269.

## Files Touched
- `domain/models/carousel.py` (theme: CarouselTheme → str)
- `infrastructure/database/models/carousel.py` (to/from-domain string passthrough)
- `api/routes/carousels/crud.py`, `application/tools/carousel/generate_carousel.py`
  (validate via enum, store `.value` string)
- `application/services/carousel/theme_resolver.py` (auto compare → `.value`; key direct)
- `api/routes/carousels/media.py`, `preview.py`,
  `application/services/carousel/design_token_utils.py`, `image_prompt_package.py`
  (`.theme.value` → `.theme`)
- `tests/unit/domain/test_carousel_theme_reference.py` (new, 5 tests)

## Test Evidence
- `mypy --strict` (rag_backend, 522 files): clean.
- `tests/unit`: **1957 passed, 1 skipped** (unchanged) + **5 new** (theme reference).
- Static gates: ruff format/lint, lint-imports, arch-ratchet, vulture, interrogate — all PASS.
- `check-integrity.sh backend` vs origin/main: 0 net-new blockers.

## QA Report
Pending (handoff to /qa-agent after the wave, per AE-0267 wave mode).

## Decision Log
D6 (string reference). G4/F2 migration-hardening ACs rendered **N/A** by the
already-varchar column (finding above); census remains as a read-only owner-run check.

## Blockers
None. Prod census ran (ssh) and is GREEN — column already `varchar(30)`, all values valid.

## Final Summary
Dev Complete: theme is a string reference, behaviour-preserving, **no migration** (prod
column already `varchar(30)`, census GREEN). All gates + integrity green. Ready to merge.
Unblocks AE-0269 (which owns the UUID-width column widening + the custom-palette table).
