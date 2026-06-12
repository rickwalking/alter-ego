# AE-0065 — Frontend: move interface in `create-workflow-controls.tsx` to its own file

Status: Done
Tier: T1
Priority: High
Type: Refactor
Area: Frontend
Owner: Unassigned
Agent Lane: architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-11
Updated: 2026-06-11

## Goal

Fix PR #11 comment #21: "move interface to its own file" in `frontend/src/app/dashboard/create/workspace/create-workflow-controls.tsx` (line 14).

## Problem

A TypeScript interface is defined inline in a component file, mixing types with UI logic.

## Scope

- Move the interface to a dedicated types file (e.g., `src/features/create/types.ts` — already created by AE-0047)
- Update imports in `create-workflow-controls.tsx`

## Non-Goals

- Do not change the interface shape or component behavior

## Acceptance Criteria

- [ ] Interface is in a dedicated types file
- [ ] Import is updated in the component file
- [ ] TypeScript compiles cleanly (npm run typecheck passes)
- [ ] All tests pass

## Affected Areas

- Frontend: `app/dashboard/create/workspace/create-workflow-controls.tsx`, `features/create/types.ts`

## Dependencies

- Blocks: None
- Blocked by: None
- Related: AE-0047 (frontend types/constants infrastructure already created)

## QA Checklist

- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Final Summary

Completed. See git log for implementation details.
