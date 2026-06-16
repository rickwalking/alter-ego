# AE-0131 — Public read-model projections (public /blog + calendar/board/analytics) — byte-identical output; blog routes behind facade

Status: Review
Tier: T2
Priority: High
Type: Task
Area: Backend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0131-read-model-projections
Kanban Card: TBD
Created: 2026-06-15
Updated: 2026-06-15

## Goal

Serve the public /blog (+ /blog/{lang}), content-calendar, workflow-board, and editorial-analytics from publishing read-model projections (instead of reading editorial/carousel aggregates directly), with byte-identical output; blog routes become thin adapters over the publishing facade. Builds on the AE-0127 origin/backfill so the public /blog can read the BlogPost projection.

## Problem

Public/editor read routes read editorial/carousel/blog aggregates directly. The roadmap exit gate wants public routes to read publication projections. Phase 6 introduces projections with identical output (additive; the embedded columns remain as a fallback).

## Scope

- Define publishing read-model/projection queries for: the public carousel /blog (+lang), content-calendar, workflow-board, and editorial-analytics.
- Route those endpoints through the publishing facade projection queries; output BYTE-IDENTICAL to today (the projection reads BlogPost-origin='carousel' rows backfilled by AE-0127, falling back to embedded columns where needed so output is unchanged).
- Blog-post CRUD routes become thin adapters over the publishing facade.
- Publishing application imports no concrete Postgres repo (port/facade only); routes import no carousel/blog ORM or get_container.

## Non-Goals

- No output change (byte-identical).
- No embedded-column drop (projection falls back to them).
- No new analytics.

## Modularization Alignment (2026-06-15)

Phase 6 of the modularization plan (§Phase 6). **Behavior-preserving + additive-only** for the IN scope — blog/publish/distribution/calendar/board/analytics responses + the public carousel /blog stay byte-identical; the migration is ADDITIVE (add origin + backfill; NO column drop); the outbox is ADDITIVE (alongside the existing after-commit publish); NO renames. The auto-publish behavior cutover + the destructive embedded-column drop are DEFERRED (documented follow-up; the approval≠release contract is already split in AE-0111). Follow `docs/architecture/module-conventions.md` + the modules/editorial+presentation pattern; reuse the platform UoW, the QA-guardian gates, and the AE-0103/0112/0122 import-contract + ratchet pattern; compose via DI at the edge (no get_container in module code). publishing is invoked BY editorial/presentation via the facade (acyclic; publishing imports no editorial/presentation internals). Precondition: Phase 5 (PR #19) merged. The checkpoint-drain rule applies to any schema-modifying migration (Phase 6's is additive ⇒ no drain needed).

## Acceptance Criteria

- [ ] THE public /blog(+lang), content-calendar, workflow-board, and editorial-analytics endpoints SHALL serve from publishing projection queries via the facade
- [ ] WHEN those endpoints are called THE responses SHALL diff to ZERO against the AE-0125 snapshots (byte-identical projections)
- [ ] Blog-post CRUD routes SHALL be thin adapters over the publishing facade; routes import no carousel/blog ORM or get_container
- [ ] Publishing application/domain SHALL import no concrete Postgres repo (port/facade only)
- [ ] WHEN gates.sh + mypy + lint-imports + pytest run THEY SHALL pass; AE-0125 safety net green

## Gherkin Scenarios

Not applicable — behavior-preserving extraction; verified by the AE-0125 safety net (diff=0).

## Delta

### ADDED

- publishing projection queries + edge DI provider (api/dependencies/publishing.py)

### MODIFIED

- api/routes/{blog_post,content_calendar,workflow_board}.py + carousel media /blog via the facade

### REMOVED

- Direct aggregate reads in the public/editor read routes

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

- Blocks: AE-0132
- Blocked by: AE-0125, AE-0126, AE-0127, AE-0128, AE-0129 (calendar/board projections may surface distribution fields)
- Related: AE-0120, AE-0123

## Implementation Plan

1. Define projection queries.
2. Route public/editor read routes + blog CRUD through the facade.
3. Verify byte-identical diff=0.

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
