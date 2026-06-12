# AE-0052 — Refactor `regenerate_carousel_presentation.py` (if chain → dict dispatch)

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

Fix PR #11 comment #4 (line 94): "inner if statement. Use dictionaries instead of complex number of if statements" in `backend/scripts/regenerate_carousel_presentation.py`.

## Problem

`_print_audit()` or other functions use a chain of sequential `if` statements to handle different audit fields. This is fragile and verbose.

## Scope

- Replace long if/elif chain with a dictionary-based dispatch or structured iteration
- Use a list of (label, value) tuples or a dict mapping field names to extractors
- Preserve exact output format

## Non-Goals

- Do not change CLI interface or flags
- Do not refactor other parts of the script

## Acceptance Criteria

- [ ] No if/elif chain longer than 3 branches for audit field printing
- [ ] Adding a new audit field requires adding a mapping entry, not a new if block
- [ ] Output format matches current behavior exactly
- [ ] ruff check, mypy pass

## Gherkin Scenarios

```gherkin
Feature: Audit output refactor

  Scenario: All audit fields printed correctly
    Given a RegenerationResult with all fields populated
    When _print_audit is called
    Then every field is printed in the expected order
    And format matches previous output
```

## Affected Areas

- Backend: `backend/scripts/regenerate_carousel_presentation.py`

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

## Final Summary

Completed. See git log for implementation details.
