# AE-0268 — P1: carousel theme as string reference (+ prod census gate)

Status: Ready
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

- [ ] **Pre-migration gate (blocking, before writing the migration):** capture prod
      `pg_typeof(carousel_projects.theme)`, the actual column DDL/CHECK, and
      `SELECT theme, count(*) FROM carousel_projects GROUP BY 1`; assert every present
      value is a current root key or `"auto"`. Output attached to this ticket. (skeptical G4)
- [ ] Migration is **expand-only/in-place** (`USING theme::text`, zero row rewrite);
      existing values round-trip; any CHECK is widened, not silently dropped.
- [ ] Recovery path is **roll-forward** (a follow-up migration), NOT `alembic downgrade`;
      a tested downgrade-failure contingency is documented. (skeptical F2)
- [ ] Migration trialed (upgrade + downgrade) on a **staging DB restored from a current,
      unsanitised prod backup**; result recorded.
- [ ] Post-deploy **monitoring query** confirms every `theme` value resolvable and row
      counts unchanged.
- [ ] All ~9 `CarouselTheme` references updated; `mypy --strict` + full `gates.sh backend`
      green; "no public/user-visible behaviour change" asserted (AE-0153 refactor path).

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
Created from AE-0267 planner breakdown.

## Files Touched
Pending.
## Test Evidence
Pending.
## QA Report
Pending.
## Decision Log
D6 (string reference), F2/G4 (migration hardening) — see arch-plan.
## Blockers
None.
## Final Summary
Pending.
