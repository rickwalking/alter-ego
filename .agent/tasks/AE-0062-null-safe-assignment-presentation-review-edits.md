# AE-0062 — Null-safe assignment in `presentation_review_edits.py`

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

Fix PR #11 comment #16: "assignment without checking for nullable values" in `backend/src/rag_backend/application/services/carousel/presentation_review_edits.py` (line 69).

## Problem

A value is assigned from a nullable source without checking for None first. If the value is None, it could cause AttributeError or TypeError downstream.

## Scope

- Review the assignment around line 69 in `presentation_review_edits.py`
- Add null check before assignment, or use `.get()` with default
- If None is valid, handle it explicitly with a guard clause or fallback

## Non-Goals

- Do not change the edit logic or output format

## Acceptance Criteria

- [ ] Nullable values are checked before assignment
- [ ] Assignment is null-safe (no AttributeError on None)
- [ ] ruff check, mypy, pytest pass

## Affected Areas

- Backend: `application/services/carousel/presentation_review_edits.py`

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
