# AE-0057 — Add null safety for property access in `artifact_manifest.py`

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

Fix PR #11 comment #10: "is it safe to access all these properties without checking? let's think about a better architect solution" in `backend/src/rag_backend/application/services/carousel/artifact_manifest.py` (line 171).

## Problem

Properties are accessed on objects without null/type checks. If the object is None or missing fields, this will raise AttributeError at runtime.

## Scope

- Review property access patterns in `artifact_manifest.py`
- Add null/type guards where properties might be None
- Use `getattr()` with defaults or explicit checks
- Consider a TypedDict or dataclass for the manifest structure

## Non-Goals

- Do not change the manifest generation output format

## Acceptance Criteria

- [ ] All dynamic property accesses have null/type guards
- [ ] No bare `.attribute` access on unvalidated objects
- [ ] ruff check, mypy, pytest pass

## Affected Areas

- Backend: `application/services/carousel/artifact_manifest.py`

## Dependencies

- Blocks: None
- Blocked by: None
- Related: AE-0042 (null-safety theme)

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked
