# AE-0054 — Move strategy classes in `strategies.py` to dedicated file

Status: QA Complete
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

Fix PR #11 comment #9: "move these classes to a new file" — the strategy route handler classes in `backend/src/rag_backend/api/routes/carousels/strategies.py` should be in their own module.

## Problem

Handler classes are co-located with route definitions, violating separation of concerns. This makes routes harder to read and classes harder to test.

## Scope

- Move strategy handler classes from `strategies.py` to a dedicated module (e.g., `api/routes/carousels/strategy_handlers.py` or `application/services/carousel/strategy_handlers.py`)
- Update imports in `strategies.py` to import from new location
- Verify no circular imports introduced

## Non-Goals

- Do not change strategy logic or behavior
- Do not change route definitions themselves

## Acceptance Criteria

- [ ] Strategy handler classes are in a dedicated file (not inline with routes)
- [ ] All existing imports are updated
- [ ] ruff check, mypy, pytest pass
- [ ] No circular imports

## Affected Areas

- Backend: `api/routes/carousels/strategies.py`, new handler module

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
