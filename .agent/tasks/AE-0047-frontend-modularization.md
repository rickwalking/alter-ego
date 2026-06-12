# AE-0047 — Frontend Modularization

Status: Dev Complete
Tier: T2
Priority: Medium
Type: Task
Area: Frontend
Owner: Unassigned
Agent Lane: developer → qa
Branch: feat/ae-0047-frontend-modularization
Kanban Card: AE-0047
Created: 2026-06-10
Updated: 2026-06-10

## Goal

Move inline interfaces, constants, and utility functions into dedicated files. Create a reusable Spinner/Loading component using React Suspense.

## Problem

PR #11 review flagged 4 frontend issues:
- `create-workflow-controls.tsx`: Interface inline → should be in `types.ts`
- `workflow-failed-card.tsx`: Constants inline → should be in `constants.ts`
- `regenerate-strategy-section.tsx`: Constants, interfaces, utils mixed with component → separate files
- `regenerate-strategy-section.tsx`: Loading state rendered inline → should use reusable Spinner + React Suspense

## Scope

### Move Interface to types.ts
- Move `CreateWorkflowControlsProps` from `create-workflow-controls.tsx` to `features/create/types.ts`
- Update import

### Move Constants to constants.ts
- Move `cardStyle` from `workflow-failed-card.tsx` to `features/create/constants.ts`
- Update import

### Modularize regenerate-strategy-section.tsx
- Constants → `features/publish/constants.ts`
- Interfaces → `features/publish/types.ts`
- Utils → `features/publish/utils.ts`
- Component stays in `regenerate-strategy-section.tsx`

### Reusable Spinner — removed from scope

Deferred to AE-0068 (consolidation of the two existing spinner
implementations). See Modularization Alignment.

## Non-Goals

- Refactoring the component logic itself
- Adding new features or changing behavior
- Modifying backend code
- Creating a full design system

## Modularization Alignment (2026-06-12)

Wave A — execute first; co-location moves match the plan's frontend
direction (module-owned types/constants/utils). Alignment:

- Use the **current** `features/create` and `features/publish` paths;
  Phase 7 renames feature folders to bounded-context names later — these
  moves make that rename cheaper, so do not invent new folder names now.
- **Spinner section removed — deferred to AE-0068** (see below): two
  spinner implementations already exist (`components/ui/spinner.tsx`,
  `components/atoms/neon-spinner.tsx`); creating a third was stale scope.
  AE-0068 owns consolidation.
- Keep moved types/constants domain-local to their feature; nothing new
  in global `components/` or `lib/` (plan: atomic folders stay
  domain-neutral, business code lives in features/modules).

## Acceptance Criteria

- [ ] `CreateWorkflowControlsProps` moved to `features/create/types.ts`
- [ ] `cardStyle` and similar constants moved to `features/create/constants.ts`
- [ ] `regenerate-strategy-section.tsx` split into constants/types/utils/component
- [ ] All original imports updated and verified
- [ ] `<Spinner />` component created with size/color/label variants
- [ ] Spinner has `aria-label` and `role="status"`
- [ ] Inline loading states in regenerate-strategy-section replaced with `<Spinner />`
- [ ] At least one area uses React `<Suspense>` with `<Spinner />` fallback
- [ ] All frontend tests pass: `cd frontend && npm test`
- [ ] TypeScript passes: `cd frontend && npm run typecheck`
- [ ] ESLint passes: `cd frontend && npm run lint`

## Gherkin Scenarios

```gherkin
Feature: Reusable Spinner Component

  Scenario: Spinner renders with custom label
    Given a Spinner component with label="Loading strategies"
    When rendered
    Then it includes text "Loading strategies" and role="status"

  Scenario: Spinner renders with default props
    Given a Spinner component with no props
    When rendered
    Then it uses medium size and no label
    And has role="status"

Feature: Component Imports

  Scenario: regenerate-strategy-section imports from types file
    Given the regenerate-strategy-section component
    When checking its imports
    Then interfaces come from "../types" or "publish/types"
    And constants come from "../constants" or "publish/constants"
```

## Delta

### ADDED

- `features/create/types.ts`
- `features/create/constants.ts`
- `features/publish/types.ts`
- `features/publish/constants.ts`
- `features/publish/utils.ts`
- `components/ui/spinner.tsx`
- Unit tests for spinner component

### MODIFIED

- `create-workflow-controls.tsx` — import from types
- `workflow-failed-card.tsx` — import from constants
- `regenerate-strategy-section.tsx` — split and import from new files

## Affected Areas

- Backend: None
- Frontend: 4 components + 6 new files
- Tests: New spinner tests
- i18n: May need spinner label key if not present

## Dependencies

- Blocks: None
- Blocked by: None
- Related: AE-0041 (no dependency, but constants pattern should align)

## Implementation Plan

1. Create `features/create/types.ts` and `constants.ts`
2. Move interface and constants; update imports
3. Create `features/publish/types.ts`, `constants.ts`, `utils.ts`
4. Split `regenerate-strategy-section.tsx`; update imports
5. Create `components/ui/spinner.tsx` with variants
6. Create spinner tests (renders, variants, accessibility)
7. Replace inline loading states in regenerate-strategy-section
8. Add React Suspense boundary where appropriate
9. Run `npm test`, `npm run typecheck`, `npm run lint`

## QA Checklist

- [ ] Code quality reviewed — no inline constants/types
- [ ] Acceptance criteria validated
- [ ] Edge cases tested — spinner in loading vs loaded state, Suspense fallback
- [ ] Accessibility checked — aria-label, role="status"

## Progress Log

### 2026-06-10

Ticket created.

## Files Touched

- frontend/src/components/ui/spinner.test.tsx (11 tests; later relocated by AE-0068)
  (modularization extraction pre-existed in base)

## Test Evidence

```
typecheck: clean; lint: 0 errors
spinner tests: 11/11 passed
```

## QA Report

Pending.

## Decision Log

Pending.

## Blockers

None.

## Final Summary

Pending.
