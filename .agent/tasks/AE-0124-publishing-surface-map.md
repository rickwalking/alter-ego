# AE-0124 — Publishing/blog/distribution surface + ownership map + migration/outbox/behavior risk analysis

Status: Review
Tier: T2
Priority: High
Type: Docs
Area: Docs/Arch
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: docs/ae-0124-publishing-surface-map
Kanban Card: TBD
Created: 2026-06-15
Updated: 2026-06-15

## Goal

Author docs/architecture/publishing-surface-ownership.md: map the blog (BlogPost + carousel-embedded), publishing/visibility/scheduling, and distribution (caption/linkedin) surfaces to writers/readers (file:line); specify the ADDITIVE migration plan (origin + backfill, no drop), the additive outbox design, and the behavior-preservation analysis (the auto-publish conflation + what stays vs defers).

## Problem

Phase 6 spans a dual blog representation, scattered distribution/visibility, and an event path without an outbox. Without a precise map + migration/outbox/behavior risk analysis, AE-0127/0128/0130/0131 cannot be scoped safely.

## Scope

- Map BlogPostModel columns (+ the missing origin) + the carousel-embedded blog/caption/linkedin columns to writers/readers (file:line).
- Specify the ADDITIVE migration: add origin (backfill 'carousel' for project-linked, 'standalone' else), backfill blog_posts rows from carousel blog_markdown/translations; NO column drop; reversible; fresh-DB upgrade + empty-autogenerate-diff drift must hold.
- Specify the additive transactional outbox (table + relay; at-least-once; idempotent) alongside the existing after-commit publish; identical payloads.
- During the migration window the embedded carousel columns REMAIN the authoritative read source (the AE-0127 backfill is one-time; ongoing carousel writes still land in the embedded columns until the deferred cutover/drop) — AE-0131 projections read them as the fallback. Document this dual-source window + the duplicate-delivery window for the outbox (AE-0130).
- Mark SEO as NOT PRESENT in the codebase today (BlogPost has meta fields but no optimizer) — deferred, out of Phase 6 scope.
- Behavior analysis: document the crud.py auto-publish conflation, what AE-0128 routes through the release command behavior-preservingly, and the DEFERRED auto-publish cutover + column drop (with the AE-0111 contract split already in place).

## Non-Goals

- No code/migration change (docs only).
- No destructive-drop design beyond marking it deferred.

## Modularization Alignment (2026-06-15)

Phase 6 of the modularization plan (§Phase 6). **Behavior-preserving + additive-only** for the IN scope — blog/publish/distribution/calendar/board/analytics responses + the public carousel /blog stay byte-identical; the migration is ADDITIVE (add origin + backfill; NO column drop); the outbox is ADDITIVE (alongside the existing after-commit publish); NO renames. The auto-publish behavior cutover + the destructive embedded-column drop are DEFERRED (documented follow-up; the approval≠release contract is already split in AE-0111). Follow `docs/architecture/module-conventions.md` + the modules/editorial+presentation pattern; reuse the platform UoW, the QA-guardian gates, and the AE-0103/0112/0122 import-contract + ratchet pattern; compose via DI at the edge (no get_container in module code). publishing is invoked BY editorial/presentation via the facade (acyclic; publishing imports no editorial/presentation internals). Precondition: Phase 5 (PR #19) merged. The checkpoint-drain rule applies to any schema-modifying migration (Phase 6's is additive ⇒ no drain needed).

## Acceptance Criteria

- [ ] THE document SHALL map every blog/publishing/distribution column + the BlogPost columns to writers/readers (file:line) and owned-vs-deferred
- [ ] THE document SHALL specify the ADDITIVE migration (origin + backfill; no drop; reversible; drift-check satisfiable)
- [ ] THE document SHALL specify the additive outbox (table + relay; at-least-once; idempotent; identical payloads)
- [ ] THE document SHALL analyze the auto-publish conflation and name what is behavior-preserving (release command) vs DEFERRED (cutover + column drop)
- [ ] WHEN AE-0127/0128/0130/0131 are planned THE map SHALL be sufficient to scope them (no unmapped surface)

## Gherkin Scenarios

Not applicable — documentation deliverable.

## Delta

### ADDED

- docs/architecture/publishing-surface-ownership.md

### MODIFIED

- docs/plans/phase-6-publishing-blog-distribution.md (link)

### REMOVED

- None

## Affected Areas

- Backend: none
- Frontend: none (Phase 7)
- Database: none (additive-only if any)
- API: none
- Tests: contract/behavior tests
- Docs: publishing surface map
- Prompts/LLM: none
- Observability: none
- Deployment: none

## Dependencies

- Blocks: AE-0127, AE-0128, AE-0130, AE-0131
- Blocked by: None
- Related: AE-0105, AE-0123

## Implementation Plan

1. Inventory blog/publishing/distribution columns + writers.
2. Design the additive migration + outbox.
3. Write the behavior-preservation analysis + deferrals.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-15

Ticket created by planner (Phase 6 breakdown).

Dev Complete (Wave A). docs/architecture/publishing-surface-ownership.md — 32 BlogPost columns + 6 carousel-embedded distribution columns mapped (8 writer surfaces, file:line); additive migration plan (origin + backfill, no drop, reversible); outbox single-durable-path design; behavior analysis (auto-publish conflation + behavior-preserving release + deferred cutover/drop AE-0133); SEO documented as read-only scorer (no optimizer) → deferred. Wave A 46 tests pass; mypy 511, integrity 0 blockers, no suppressions.

## Files Touched

docs/architecture/publishing-surface-ownership.md

## Test Evidence

Pending.

## QA Report

Phase 6 Wave A batch QA — converged PASS in 2 independent rounds (0 findings). See `.agent/reports/phase-6-wave-a.qa.md`.

## Decision Log

Pending.

## Blockers

None.

## Final Summary

Pending.
