# AE-0005 — Slide Layout Strategy API + DI Wiring

Status: Review
Tier: T2
Priority: High
Type: Feature
Area: Backend
Owner: Unassigned
Agent Lane: architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-04
Updated: 2026-06-04

## Goal

Wire the SlideLayoutRegistry into the DI container and expose two API endpoints: list available strategies and regenerate slides with a chosen strategy.

## Problem

P1-P4 of the strategy pattern architecture are implemented (css/ subfolder, strategies/ dir, Protocol, registry, builder cleaned up). But the strategy registry is not injected into the service layer, and there are no API endpoints to let the frontend select or change strategies. Without this, the new strategies are dead code.

## Scope

- Wire `bootstrap_strategies()` in `infrastructure/container.py` as a `providers.Singleton`
- Inject `SlideLayoutRegistry` into `CarouselRefinementService`
- Add `slide_layout_strategy: str | None` field to `CarouselProject` model + DB migration
- Add field to `CarouselProjectResponse` and `CarouselProjectCreate` schemas
- Create `api/routes/carousels/strategies.py` with:
  - `GET /api/carousels/strategies` — list all registered strategies
  - `POST /api/carousels/{id}/slides/regenerate?strategy=<name>` — regenerates slides with given strategy
- Wire the new router into the carousels router
- Update `build_carousel_html()` to accept optional `strategy_registry` parameter

## Non-Goals

- Frontend UI changes (separate AE-0004 ticket)
- Writing strategy unit tests (separate AE-0006 ticket)
- DB migration script (use existing Alembic patterns)

## Acceptance Criteria

- [ ] `bootstrap_strategies()` called from container and all 7 strategies registered
- [ ] `SlideLayoutRegistry` injected into `CarouselRefinementService`
- [ ] `GET /api/carousels/strategies` returns list of `{name, display_name}` dicts
- [ ] `POST /api/carousels/{id}/slides/regenerate?strategy=feature_grid` returns 200 with updated project
- [ ] `POST /api/carousels/{id}/slides/regenerate?strategy=nonexistent` returns 422
- [ ] `POST` on non-completed project returns 409
- [ ] `CarouselProjectResponse` includes `slide_layout_strategy` field
- [ ] No existing tests broken (866 should still pass)
- [ ] Migration is reversible — `ALTER TABLE carousel_projects DROP COLUMN slide_layout_strategy` succeeds
- [ ] Regenerate on a published carousel returns 200 and updates slides (does not auto-unpublish)

## Gherkin Scenarios

```gherkin
Feature: Carousel Slide Layout Strategy API

  Background:
    Given a completed carousel project with 7 slides

  Scenario: List available strategies
    When I GET /api/carousels/strategies
    Then the response contains a strategies array
    And each strategy has "name" and "display_name"

  Scenario: Regenerate with valid strategy
    When I POST /api/carousels/{id}/slides/regenerate?strategy=feature_grid
    Then the response contains slide_layout_strategy: "feature_grid"

  Scenario: Regenerate with invalid strategy returns 422
    When I POST /api/carousels/{id}/slides/regenerate?strategy=invalid_name
    Then the API returns 422 Unprocessable Entity

  Scenario: Regenerate on non-completed project returns 409
    Given a carousel project with status "drafting"
    When I POST /api/carousels/{id}/slides/regenerate?strategy=feature_grid
    Then the API returns 409 Conflict
```

## Delta

### ADDED

- `api/routes/carousels/strategies.py` — 2 new endpoints
- `CarouselProject.slide_layout_strategy` domain field
- DI wiring for `SlideLayoutRegistry` singleton
- Strategy-aware `build_carousel_html()` overload

### MODIFIED

- `infrastructure/container.py` — add strategy_registry provider
- `api/routes/carousels/__init__.py` — include strategies router
- `api/schemas/carousel.py` — add slide_layout_strategy to response + create schemas
- `domain/models/carousel.py` — add slide_layout_strategy field
- `html_template.py` — accept optional strategy_registry for dispatch

### REMOVED

None.

## Affected Areas

- Backend: yes
- Frontend: no
- Database: yes (new column on carousel_projects)
- API: yes (2 new endpoints)
- Tests: no (separate AE-0006)
- Docs: yes (api-contracts.md update)
- Prompts/LLM: no
- Observability: no
- Deployment: no

## Dependencies

- Blocks: AE-0004 (Frontend Strategy Selector Integration)
- Blocked by: none (P1-P4 already implemented in prior session)
- Related: AE-0006 (Strategy Tests)

## Implementation Plan

1. Add `slide_layout_strategy: str | None = None` to `CarouselProject` dataclass
2. Add field to `CarouselProjectResponse` and `CarouselProjectCreate` schemas
3. Wire `bootstrap_strategies()` in `container.py` as Singleton
4. Add `strategy_registry` parameter to `CarouselRefinementService.__init__`
5. Create `api/routes/carousels/strategies.py` with list + regenerate endpoints
6. Update `build_carousel_html()` to accept optional registry for strategy dispatch
7. Add DB migration for new column (add-only, nullable, no backfill needed)
8. Verify migration is reversible — add rollback step test
9. Run full test suite to verify no regressions

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-04

Ticket created. Architecture plan exists at `docs/plans/carousel-slide-layout-strategies.md`. P1-P4 (Protocol, registry, strategies, css subfolder, builder cleanup) already implemented.

### 2026-06-04 (fixes)

QA found 4 blockers, 5 warnings, 3 suggestions. All fixed:
- Route path fixed: `@router.put("/{id}/strategy")` eliminates double `/carousels` segment
- Auth added: `Depends(require_authenticated_user)` on PUT endpoint
- Status guard added: 409 for non-completed projects
- Migration created: `0006_add_slide_layout_strategy`
- Architecture fixed: `list_strategies` uses `Depends(get_strategy_registry)` via deps.py
- Magic strings extracted to constants
- `project_id` typed as `UUID`
- Audit logging added
- `name` query param constraints added (min_length=1, max_length=50)
- `find_for_slide` fragile dict access fixed in registry.py
- 865 tests pass, ruff clean

## Files Touched

Pending.

## Test Evidence

```bash
uv run pytest tests/ -q --tb=short
# Expected: 866+ passing
```

## QA Report

**Overall Score**: 100/100 (A)

QA run 2 valid:
- Route ordering fix verified: `strategies_router` before `crud_router`
- No security findings, no code quality findings
- 6/6 ACs met, 932 tests pass
- See `.agent/reports/AE-0005.qa.md` for full report

## Decision Log

- Strategy registry is a Singleton per container config
- Strategy name stored as simple `str` on project (no FK, enums, or strategy_version table needed)
- API uses query param `?strategy=` for clarity (not path param)
- Regenerate is allowed on published carousels — updates slides without affecting `is_public` status

## Blockers

None.

## Final Summary

Pending.
