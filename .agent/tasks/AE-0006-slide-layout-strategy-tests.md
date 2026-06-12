# AE-0006 — Slide Layout Strategy Tests

Status: Intake
Tier: T2
Priority: Medium
Type: Tests
Area: Tests
Owner: Unassigned
Agent Lane: architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-04
Updated: 2026-06-04

## Goal

Write Gherkin feature file, unit tests per strategy, registry tests, API integration tests, and property tests for the slide layout strategy pattern.

## Problem

The 7 strategy implementations (intro_hero, hero_content, stat_card_grid, feature_grid, insight_quote, numbered_list, cta_centered) have zero test coverage. The registry and new API endpoints also lack tests. This is a gap for the 90%+ branch coverage requirement.

## Scope

- Gherkin `.feature` file at `tests/features/carousel_slide_layout_strategies.feature`
- Unit tests: `tests/unit/application/strategies/` directory with:
  - `test_strategy_interface.py` — Protocol contract tests for all strategies
  - `test_stat_card_grid.py` — stat grid rendering, fallback, overflow
  - `test_feature_grid.py` — feature card rendering, fallback, overflow
  - `test_insight_quote.py` — quote card, attribution, fallback
  - `test_numbered_list.py` — numbered steps, fallback
  - `test_registry.py` — register, get, list, find_for_slide, duplicates, not-found
- Integration tests: `tests/integration/test_strategy_endpoints.py` for API endpoints
- Property tests: `tests/property/test_strategy_properties.py` using Hypothesis

## Non-Goals

- Mutation testing (weeks away per CLAUDE.md)
- E2E tests (in frontend test suite)
- Benchmarking strategy rendering performance

## Acceptance Criteria

- [ ] Gherkin `.feature` file covers 10 scenarios (selection, fallback, persistence, orthogonality, error)
- [ ] All 7 strategies tested via Protocol contract (interface compliance)
- [ ] Each structured strategy (stat_card_grid, feature_grid, insight_quote, numbered_list) tested for:
  - Happy path: renders correct HTML structure
  - Fallback: degrades to hero_content when data is None
  - Overflow: caps at MAX_FEATURE_ITEMS (4)
- [ ] Registry tested for: register+get, duplicate raises, not-found raises, list, find_for_slide matching + fallback
- [ ] API integration tests for: valid strategy, invalid strategy (422), non-completed project (409), list endpoints
- [ ] Property tests cover: any string input produces valid HTML, all theme×strategy combos produce output
- [ ] All tests pass with 90%+ branch coverage on new code

## Gherkin Scenarios

```gherkin
Feature: Carousel Slide Layout Strategies

  Background:
    Given a completed carousel project with 7 slides
    And the project has persisted SlideData with features, stats, and insight

  Scenario: Select stat_card_grid strategy
    Given a carousel with 3 content slides
    When I select the "stat_card_grid" strategy
    Then content slides render stats as 3-column cards
    And the HTML contains ".stat-card-grid" selector

  Scenario: Select feature_grid strategy
    Given a carousel with 3 content slides
    When I select the "feature_grid" strategy
    Then content slides render features as a 2-column grid

  Scenario: Select insight_quote strategy
    Given a carousel with a closing slide containing insight data
    When I select the "insight_quote" strategy
    Then the closing slide renders an accent-bordered quote card

  Scenario: Fallback for missing data
    Given a carousel with no stats data
    When I select the "stat_card_grid" strategy
    Then the strategy falls back to "hero_content" layout

  Scenario: Intro and CTA slides ignore strategy
    Given any selected strategy
    When rendering an intro or CTA slide
    Then the intro uses "intro_hero" layout regardless

  Scenario: Strategy not found returns 422
    Given an invalid strategy name "nonexistent"
    When I POST to /slides/regenerate?strategy=nonexistent
    Then the API returns 422 Unprocessable Entity

  Scenario: List available strategies
    When I GET /strategies
    Then the response contains a strategies array

  Scenario: Active strategy persisted and readable
    Given I have applied the "feature_grid" strategy
    When I GET the carousel project
    Then the response includes slide_layout_strategy: "feature_grid"

  Scenario: Theme and strategy are orthogonal
    Given any selected strategy
    When I apply a "cybersecurity" theme
    Then the strategy renders with cybersecurity colors

  Scenario: Bilingual rendering with strategy
    Given a bilingual carousel (pt + en)
    When I select any strategy
    Then EN slides use the same strategy layout with translated text
```

## Delta

### ADDED

- `tests/features/carousel_slide_layout_strategies.feature`
- `tests/unit/application/strategies/test_strategy_interface.py`
- `tests/unit/application/strategies/test_stat_card_grid.py`
- `tests/unit/application/strategies/test_feature_grid.py`
- `tests/unit/application/strategies/test_insight_quote.py`
- `tests/unit/application/strategies/test_numbered_list.py`
- `tests/unit/application/strategies/test_registry.py`
- `tests/integration/test_strategy_endpoints.py`
- `tests/property/test_strategy_properties.py`

### MODIFIED

None.

### REMOVED

None.

## Affected Areas

- Backend: no
- Frontend: no
- Database: no
- API: no
- Tests: yes (9 new test files)
- Docs: no
- Prompts/LLM: no
- Observability: no
- Deployment: no

## Dependencies

- Blocks: none
- Blocked by: AE-0005 (Strategy API + DI Wiring) — needed for integration tests
- Related: none

## Implementation Plan

1. Write Gherkin `.feature` file (10 scenarios)
2. Create test fixtures: `sample_slide_with_stats`, `sample_slide_with_features`, `sample_slide_with_insight`, `all_strategies`, `registry`
3. Write Protocol contract tests (all strategies)
4. Write per-strategy unit tests with fallback + overflow cases
5. Write registry unit tests
6. Write API integration tests
7. Write property tests (Hypothesis)
8. Verify 90%+ branch coverage on `strategies/` and `strategies/registry.py`

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-04

Ticket created.

## Files Touched

Pending.

## Test Evidence

```bash
cd backend
uv run pytest tests/unit/application/strategies/ -v --tb=short
uv run pytest tests/integration/test_strategy_endpoints.py -v --tb=short
uv run pytest tests/property/ -v --tb=short
uv run pytest --cov=rag_backend.application.services.carousel_template.strategies
```

## QA Report

Pending.

## Decision Log

- Tests use StrategyNotFoundError from domain.protocols (not custom per-test exception)
- Fixtures use existing `sample_project` and `sample_theme` conftest fixtures
- Property tests use Hypothesis `@given` with `st.text()` for brute-force HTML validation
- Maximum 10 scenarios to keep the feature file readable

## Blockers

Integration tests blocked by AE-0005 (API must exist first). Unit tests are independent.

## Final Summary

Pending.
