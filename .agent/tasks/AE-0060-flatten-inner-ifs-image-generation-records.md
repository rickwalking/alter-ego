# AE-0060 — Flatten inner if statements in `image_generation_records.py`

Status: Intake
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

Fix PR #11 comment #14: "inner if statement" in `backend/src/rag_backend/application/services/carousel/image_generation_records.py` (line 102).

## Problem

Nested if statements make the code harder to read and test. Early returns and guard clauses should be used instead.

## Scope

- Review the function around line 102 in `image_generation_records.py`
- Flatten nested ifs with early returns and guard clauses
- No functional changes

## Non-Goals

- Do not change image generation logic or database queries

## Acceptance Criteria

- [ ] No if/else nesting deeper than 2 levels
- [ ] Guard clauses used instead of nested ifs
- [ ] ruff check, mypy, pytest pass

## Affected Areas

- Backend: `application/services/carousel/image_generation_records.py`

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
