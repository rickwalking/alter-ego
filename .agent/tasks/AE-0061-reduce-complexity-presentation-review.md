# AE-0061 — Reduce complexity in `presentation_review.py`

Status: Intake
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

Fix PR #11 comment #15: "very complex function" in `backend/src/rag_backend/application/services/carousel/presentation_review.py` (line 46).

## Problem

A function in `presentation_review.py` has high cyclomatic complexity, making it hard to test and maintain.

## Scope

- Identify the complex function around line 46
- Extract logical blocks into named helper functions
- Reduce cyclomatic complexity below 10 (C901 threshold)

## Non-Goals

- Do not change presentation review logic or output

## Acceptance Criteria

- [ ] Cyclomatic complexity ≤ 10 for each function
- [ ] Max 8 branches per function
- [ ] Max 50 statements per function
- [ ] ruff check, mypy, pytest pass

## Affected Areas

- Backend: `application/services/carousel/presentation_review.py`

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
