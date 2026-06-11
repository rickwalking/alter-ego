# AE-0067 — Frontend: split constants, interfaces, utils from `regenerate-strategy-section.tsx`

Status: Intake
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

Fix PR #11 comment #23: "constants, interfaces and utils functions to its own file" in `frontend/src/features/publish/components/regenerate-strategy-section.tsx` (line 21).

## Problem

A component file contains inline constants, interfaces, and utility functions. These should be in dedicated files (`constants.ts`, `types.ts`, `utils.ts`) for modularity.

## Scope

- Move constants to `src/features/publish/constants.ts` (already created by AE-0047)
- Move interfaces to `src/features/publish/types.ts` (already created by AE-0047)
- Move utility functions to `src/features/publish/utils.ts` (already created by AE-0047)
- Update imports in the component file

## Non-Goals

- Do not change constants, interfaces, utils, or component behavior

## Acceptance Criteria

- [ ] Constants are in the feature's constants file
- [ ] Interfaces/types are in the feature's types file
- [ ] Utility functions are in the feature's utils file
- [ ] Imports are updated in the component file
- [ ] TypeScript compiles cleanly (npm run typecheck passes)
- [ ] All tests pass

## Affected Areas

- Frontend: `features/publish/components/regenerate-strategy-section.tsx`, `features/publish/constants.ts`, `features/publish/types.ts`, `features/publish/utils.ts`

## Dependencies

- Blocks: None
- Blocked by: None
- Related: AE-0047 (frontend infrastructure already created)

## QA Checklist

- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Orphan/unfinished code checked
