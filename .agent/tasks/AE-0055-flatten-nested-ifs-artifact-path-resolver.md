# AE-0055 — Flatten nested if statements in `artifact_path_resolver.py`

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

Fix PR #11 comment #11: "inner if statements" in `backend/src/rag_backend/application/services/carousel/artifact_path_resolver.py` (line 46).

## Problem

Functions in `artifact_path_resolver.py` have nested if statements that should use early returns / guard clauses instead.

## Scope

- Review all functions in `artifact_path_resolver.py` for nested if statements
- Flatten with early returns and guard clauses
- No functional changes

## Non-Goals

- Do not change the resolver logic or path computation

## Acceptance Criteria

- [ ] No if/else nesting deeper than 2 levels
- [ ] Guard clauses used instead of nested ifs
- [ ] ruff check, mypy, pytest pass

## Affected Areas

- Backend: `application/services/carousel/artifact_path_resolver.py`

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
