# AE-0128 — Visibility + scheduling behind publishing ports; carousel publish via the release command (behavior-preserving)

Status: Ready
Tier: T2
Priority: High
Type: Task
Area: Backend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0128-publishing-visibility-release
Kanban Card: TBD
Created: 2026-06-15
Updated: 2026-06-15

## Goal

Move public visibility (is_public) + scheduling behind publishing application ports; route the carousel publish flow (crud.py is_public=True) through a publishing-module RELEASE command that does EXACTLY what it does today (behavior-preserving — no auto-publish change). Build on the AE-0111 approval≠release contract split.

## Problem

Visibility (is_public) + scheduling are set directly in carousel/blog routes/services. Publishing should own release + scheduling behind a facade — but behavior-preservingly (the release command replicates the current publish flow; the auto-publish cutover is deferred).

## Scope

- Define publishing ports for release (set public visibility) + scheduling; back them with adapters via a publishing ACL/owner (in modules/publishing/infrastructure — the only publishing code touching the carousel/blog ORM for these writes).
- Route crud.py publish_carousel's is_public write through the publishing release command — IDENTICAL behavior (still sets is_public=True under the same preconditions); no auto-publish change.
- Move the BlogPost scheduled_publish_service behind the publishing facade (behavior-preserving).
- Route the STANDALONE blog visibility routes (blog_post_workflow.py publish/unpublish/schedule) through the publishing visibility/schedule ports (behavior-preserving; diff=0).
- Commit via the platform UoW; routes stop writing is_public/schedule directly.

## Non-Goals

- No auto-publish behavior change (deferred; contract split honored).
- No destructive migration.
- No distribution (AE-0129).

## Modularization Alignment (2026-06-15)

Phase 6 of the modularization plan (§Phase 6). **Behavior-preserving + additive-only** for the IN scope — blog/publish/distribution/calendar/board/analytics responses + the public carousel /blog stay byte-identical; the migration is ADDITIVE (add origin + backfill; NO column drop); the outbox is ADDITIVE (alongside the existing after-commit publish); NO renames. The auto-publish behavior cutover + the destructive embedded-column drop are DEFERRED (documented follow-up; the approval≠release contract is already split in AE-0111). Follow `docs/architecture/module-conventions.md` + the modules/editorial+presentation pattern; reuse the platform UoW, the QA-guardian gates, and the AE-0103/0112/0122 import-contract + ratchet pattern; compose via DI at the edge (no get_container in module code). publishing is invoked BY editorial/presentation via the facade (acyclic; publishing imports no editorial/presentation internals). Precondition: Phase 5 (PR #19) merged. The checkpoint-drain rule applies to any schema-modifying migration (Phase 6's is additive ⇒ no drain needed).

## Acceptance Criteria

- [ ] Public visibility (is_public) + scheduling writes SHALL go through the publishing release/schedule ports (no direct route/service write of those)
- [ ] THE carousel publish flow SHALL route through the publishing release command with IDENTICAL behavior (same preconditions, still sets is_public; no auto-publish change)
- [ ] THE publishing ACL/owner SHALL be the only publishing code importing the carousel/blog ORM for these writes; publishing application/domain import no ORM
- [ ] WHEN the AE-0125 safety net runs THE publish/visibility responses SHALL diff to ZERO
- [ ] THE standalone blog publish/unpublish/schedule routes (blog_post_workflow.py) SHALL route through the publishing visibility/schedule ports with diff=0 against the AE-0125 snapshots
- [ ] WHEN gates.sh + mypy + lint-imports + pytest run THEY SHALL pass with no behavior change

## Gherkin Scenarios

Not applicable — behavior-preserving extraction; verified by the AE-0125 safety net.

## Delta

### ADDED

- publishing release + schedule ports/adapters + ACL/owner; release command

### MODIFIED

- api/routes/carousels/crud.py (publish via release command), scheduled_publish_service via facade

### REMOVED

- Direct is_public/schedule writes scattered in routes/services

## Affected Areas

- Backend: publishing module
- Frontend: none (Phase 7)
- Database: none (additive-only if any)
- API: publishing/blog/read routes
- Tests: contract/behavior tests
- Docs: references conventions
- Prompts/LLM: none
- Observability: none
- Deployment: none

## Dependencies

- Blocks: AE-0131, AE-0132
- Blocked by: AE-0125, AE-0126
- Related: AE-0111, AE-0123

## Implementation Plan

1. Define release/schedule ports + ACL/owner.
2. Route crud publish + scheduling through them (identical behavior).
3. Verify safety net diff=0.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-15

Ticket created by planner (Phase 6 breakdown).

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Decision Log

Pending.

## Blockers

None.

## Final Summary

Pending.
