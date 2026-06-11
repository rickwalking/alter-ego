# AE-0059 — Split large function in `editorial_distribution_persist.py`

Status: QA Complete
Tier: T2
Priority: Medium
Type: Refactor
Area: Backend
Owner: Unassigned
Agent Lane: architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-11
Updated: 2026-06-11

## Goal

Fix PR #11 comment #13: "very large function" in `backend/src/rag_backend/application/services/carousel/editorial_distribution_persist.py` (line 44).

## Problem

A function in `editorial_distribution_persist.py` exceeds reasonable size limits (max 50 statements, max 400 lines per file). It should be split into smaller focused functions.

## Scope

- Identify the large function (around line 44)
- Extract discrete steps into named helper functions
- Each helper has a single responsibility
- Reduce function size to under 50 statements

## Non-Goals

- Do not change persistence behavior or schema

## Acceptance Criteria

- [ ] The large function is split into ≤50 statement helpers
- [ ] Each helper has a clear single responsibility
- [ ] ruff check, mypy, pytest pass

## Affected Areas

- Backend: `application/services/carousel/editorial_distribution_persist.py`

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
