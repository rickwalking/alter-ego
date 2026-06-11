# AE-0063 — Extract magic strings and simplify if chain in `carousel_presentation_adapters.py`

Status: Done
Tier: T1
Priority: High
Type: Refactor
Area: Backend
Owner: Unassigned
Agent Lane: architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-11
Updated: 2026-06-11

## Goal

Fix 2 unresolved PR #11 comments on `backend/src/rag_backend/domain/models/carousel_presentation_adapters.py`:
- Comment #18 (line 78): "magic strings"
- Comment #19 (line 102): "magic strings, very complex if statements chain"

## Problem

Inline string literals are used throughout the adapter functions, and a long if/elif chain handles different presentation types in a brittle way.

## Scope

- Extract all inline string literals to module-level constants
- Replace long if/elif chain with dictionary dispatch or strategy pattern
- No functional changes

## Non-Goals

- Do not change the adapter output format or behavior

## Acceptance Criteria

- [ ] No magic strings in function bodies
- [ ] No if/elif chain longer than 3 branches for type dispatch
- [ ] Adding a new presentation type requires adding a mapping entry, not a new if block
- [ ] ruff check, mypy, pytest pass

## Affected Areas

- Backend: `domain/models/carousel_presentation_adapters.py`

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
