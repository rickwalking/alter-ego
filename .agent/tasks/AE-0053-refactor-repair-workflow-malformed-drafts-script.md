# AE-0053 — Refactor `repair_workflow_malformed_drafts.py` (magic strings, long functions, nested ifs)

Status: Intake
Tier: T2
Priority: Medium
Type: Refactor
Area: Backend/Scripts
Owner: Unassigned
Agent Lane: architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-11
Updated: 2026-06-11

## Goal

Fix 3 unresolved PR #11 comments on `backend/scripts/repair_workflow_malformed_drafts.py`:
- Comment #5 (line 69): "magic string"
- Comment #6 (line 62): "very long/complex function"
- Comment #7 (line 155): "inner if statement"

## Problem

`_build_locale_presentation()` is a long, complex function with nested if/elif chains for slide_type dispatch and inline string literals. Adding new slide types requires modifying the function.

## Scope

- Extract magic strings (slide type names, field keys) to module-level constants
- Split `_build_locale_presentation()` into per-type builder functions with a dispatch dict
- Flatten nested if statements with early returns
- All existing functionality preserved

## Non-Goals

- Do not change the CLI interface
- Do not change SQL or workflow engine interactions

## Acceptance Criteria

- [ ] No magic strings in function bodies — all extracted to named constants
- [ ] `_build_locale_presentation()` has max 8 branches, 50 statements
- [ ] Each slide type has its own builder function or handler
- [ ] Adding a new slide type requires adding a handler, not modifying an existing function
- [ ] ruff check, mypy pass

## Gherkin Scenarios

```gherkin
Feature: Script refactor

  Scenario: All slide types still build correctly
    Given a malformed draft with intro, summary, closing slides
    When _build_locale_presentation is called
    Then each slide type produces the correct structure
```

## Affected Areas

- Backend: `backend/scripts/repair_workflow_malformed_drafts.py`

## Dependencies

- Blocks: None
- Blocked by: None
- Related: None

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked
