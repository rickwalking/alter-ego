# AE-0232 — Docs quick wins: status headers + ADR-0009 accepted

Status: Intake
Tier: T1
Priority: Low
Type: Quality
Area: Docs
Owner: Unassigned
Branch: TBD
Created: 2026-06-18
Updated: 2026-06-18
Source: architect plan — `.agent/reports/frontend-migrations-and-docs.arch-plan.md` (Thread B1). Parent: AE-0231.

## Goal
Cheap, high-value doc fixes: add missing Status headers and finalize ADR-0009.

## Problem
`docs/backend/carousel-pipeline-plan.md` (and a few plans) lack a `Status:` header,
so active-vs-done is ambiguous. ADR-0009 (domain modular monolith) is still
"Proposed" though the implementation is live.

## Scope
- Add `Status:` headers to unmarked plan docs.
- Flip ADR-0009 `Proposed → Accepted` (with a one-line rationale), or document why not.
- (NOTE: ADR-011/012 are already in the CLAUDE.md index — do NOT re-add.)

## Non-Goals
- No content rewrites; just status/metadata.

## Acceptance Criteria
- [ ] Unmarked active plans carry a `Status:` header.
- [ ] ADR-0009 status resolved (Accepted with rationale, or documented decision).

## Dependencies
- Parent: AE-0231.

## Progress Log
### 2026-06-18
Created from the architect plan (Thread B1).

## Files Touched
Pending.
## Test Evidence
Pending.
## QA Report
Pending.
## Blockers
None.
