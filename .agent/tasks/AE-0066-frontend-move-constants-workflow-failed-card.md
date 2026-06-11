# AE-0066 — Frontend: move constants in `workflow-failed-card.tsx` to constants file

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

Fix PR #11 comment #22: "move constants to its own file (constants)" in `frontend/src/features/create/components/workflow-failed-card.tsx` (line 14).

## Problem

Constants are defined inline in a component file. They should be in a dedicated constants file for reuse and maintainability.

## Scope

- Move constants from `workflow-failed-card.tsx` to `src/features/create/constants.ts` (already created by AE-0047)
- Update imports in the component file

## Non-Goals

- Do not change constant values or component behavior

## Acceptance Criteria

- [ ] Constants are in the feature's constants file
- [ ] Import is updated in the component file
- [ ] TypeScript compiles cleanly (npm run typecheck passes)
- [ ] All tests pass

## Affected Areas

- Frontend: `features/create/components/workflow-failed-card.tsx`, `features/create/constants.ts`

## Dependencies

- Blocks: None
- Blocked by: None
- Related: AE-0047 (frontend constants infrastructure already created)

## QA Checklist

- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Orphan/unfinished code checked

## Final Summary

Completed. See git log for implementation details.
