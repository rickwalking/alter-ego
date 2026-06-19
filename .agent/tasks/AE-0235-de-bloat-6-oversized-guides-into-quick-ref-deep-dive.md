# AE-0235 — De-bloat 6 oversized guides into quick-ref + deep-dive

Status: Intake
Tier: T2
Priority: Low
Type: Quality
Area: Docs
Owner: Unassigned
Branch: TBD
Created: 2026-06-18
Updated: 2026-06-18
Source: architect plan — `.agent/reports/frontend-migrations-and-docs.arch-plan.md` (Thread B4). Parent: AE-0231.

## Goal
Bring the 6 oversized guides under control (the <400-line norm) without losing content.

## Problem
6 guides are 1.7k–2.3k lines: VITEST_TESTING_GUIDE (2333), ZOD_VALIDATION_GUIDE (2009),
react-2026-best-practices (1939), react-components-guide-2026 (1765), style-guide-2026
(2134), minimizing-useeffect-guide (2107). Hard to scan; violate the doc norm.

## Scope
- Per guide: extract a <300-line quick-reference + link a deep-dive (or trim duplication).
- Incremental: one guide per PR is fine. Start with VITEST + ZOD.

## Non-Goals
- No change to the technical guidance itself (reorganize, don't rewrite).

## Acceptance Criteria
- [ ] Each of the 6 has a <300-line quick-ref entry point; deep content linked.
- [ ] Inbound links (CLAUDE.md/frontend CLAUDE.md) updated to the quick-ref.

## Dependencies
- Parent: AE-0231. Largest chunk; do last / incrementally.

## Progress Log
### 2026-06-18
Created from the architect plan (Thread B4).

## Files Touched
Pending.
## Test Evidence
Pending.
## QA Report
Pending.
## Blockers
None.
