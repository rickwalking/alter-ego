# AE-0051 — Refactor `recover_carousel_image_generations.py` (complex function, nested ifs, boolean trap)

Status: Done
Tier: T1
Priority: High
Type: Refactor
Area: Backend/Scripts
Owner: Unassigned
Agent Lane: architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-11
Updated: 2026-06-11

## Goal

Fix 3 unresolved PR #11 comments on `backend/scripts/recover_carousel_image_generations.py`:
- Comment #1 (line 126): "very complex if statements. Inner statements, prefer early return"
- Comment #2 (line 104): "very complex function"
- Comment #3 (line 108): "using boolean as a parameter is a antipattern"

## Problem

`recover_project()` is a large function with deeply nested if/else blocks and a boolean `dry_run` parameter that makes call sites ambiguous.

## Scope

- Refactor `recover_project()` — extract helper functions, flatten nested ifs with early returns
- Replace boolean `dry_run` with an enum or TypedDict command object
- Ensure any `--dry-run` CLI flag still works correctly
- All existing functionality preserved

## Non-Goals

- Do not restructure the CLI argument parsing
- Do not change SQL queries

## Acceptance Criteria

- [ ] `recover_project()` has max 3 parameters (no bare booleans)
- [ ] No nested if/else deeper than 2 levels
- [ ] Each function has max 8 branches, max 50 statements
- [ ] Script still works with `--dry-run` and `--project-id` flags

## Gherkin Scenarios

```gherkin
Feature: Recovery script refactor

  Scenario: dry_run flag controls DB writes
    Given a project with unrecovered slides
    When running with --dry-run
    Then prints what would be done
    And does not write to the database

  Scenario: project-id filter works
    Given multiple carousel projects
    When running with --project-id UUID
    Then only processes the specified project
```

## Affected Areas

- Backend: `backend/scripts/recover_carousel_image_generations.py`
- Tests: None (scripts are not tested)

## Dependencies

- Blocks: None
- Blocked by: None
- Related: AE-0041 (boolean→enum pattern)

## QA Checklist

- [ ] Security reviewed — no new code execution paths
- [ ] Code quality reviewed — ruff, mypy pass
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Final Summary

Completed. See git log for implementation details.
