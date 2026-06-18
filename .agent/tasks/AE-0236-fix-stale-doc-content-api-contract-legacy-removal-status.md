# AE-0236 — Fix stale doc content (API_CONTRACT, legacy-removal status)

Status: Intake
Tier: T1
Priority: Low
Type: Quality
Area: Docs
Owner: Unassigned
Branch: TBD
Created: 2026-06-18
Updated: 2026-06-18
Source: architect plan — `.agent/reports/frontend-migrations-and-docs.arch-plan.md` (Thread B5). Parent: AE-0231.

## Goal
Correct docs whose content no longer matches the codebase.

## Problem
- `architecture/API_CONTRACT.md` references removed UI (ChatInterface/TopicForm).
- `plans/frontend-legacy-removal.md` status needs verification against the live tree
  (mark Done if those legacy components are gone).
- `guides/qa-checkpoints.md` may have TODO/MISSING markers to resolve.

## Scope
- Update API_CONTRACT to drop deprecated component examples (link OpenAPI where apt).
- Verify ChatInterface/TopicForm absence; set legacy-removal plan status accordingly.
- Resolve any TODO/MISSING markers in qa-checkpoints.md.

## Non-Goals
- No code changes; verify-and-update docs only.

## Acceptance Criteria
- [ ] API_CONTRACT has no references to removed UI components.
- [ ] frontend-legacy-removal status reflects the live tree.
- [ ] No unresolved TODO/MISSING markers in qa-checkpoints.md.

## Dependencies
- Parent: AE-0231. Independent of B2/B3/B4.

## Progress Log
### 2026-06-18
Created from the architect plan (Thread B5).

## Files Touched
Pending.
## Test Evidence
Pending.
## QA Report
Pending.
## Blockers
None.
