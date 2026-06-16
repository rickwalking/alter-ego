# AE-0123 — Phase 6 epic: Separate Publishing, Blog, and Distribution

Status: Review
Tier: T3
Priority: High
Type: Epic
Area: Cross-cutting
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: N/A (epic; sub-tickets carry branches)
Kanban Card: TBD
Created: 2026-06-15
Updated: 2026-06-15

## Goal

Extract a publishing bounded context (public visibility + scheduling, the one BlogPost aggregate with origin, distribution, public read-model projections, transactional outbox) behind a facade; editorial/presentation invoke publishing via a port. Tracks AE-0124..0132; the deferred auto-publish cutover + column drop are tracked separately by AE-0133 (Intake). Scope = behavior-preserving + additive-only; auto-publish cutover + embedded-column drop DEFERRED.

## Problem

Blog has a dual representation (first-class BlogPost + carousel-embedded blog_markdown); distribution (captions/linkedin) + visibility (is_public) + scheduling are scattered across carousel routes/services; events lack a durable outbox. Phase 6 consolidates publishing/blog/distribution into a module, additively + behavior-preserving.

## Scope

- Track + integrate children AE-0124 (map/risk), AE-0125 (safety net), AE-0126 (skeleton), AE-0127 (origin+additive migration), AE-0128 (visibility/scheduling/release command), AE-0129 (distribution), AE-0130 (outbox), AE-0131 (read-model projections), AE-0132 (import contracts + exit gate + deferred-cutover docs).
- IN: behavior-preserving extraction + additive migration (origin + backfill, no drop) + additive outbox + byte-identical projections.
- DEFERRED (documented): the auto-publish behavior cutover + the destructive embedded-column drop.
- Enforce the epic exit gate below before closing.

## Non-Goals

- No destructive column drop (deferred).
- No auto-publish behavior change cutover (contract split only; deferred).
- No CarouselArticle table (it's a read projection).
- No renames; no frontend changes (Phase 7).

## Modularization Alignment (2026-06-15)

Phase 6 of the modularization plan (§Phase 6). **Behavior-preserving + additive-only** for the IN scope — blog/publish/distribution/calendar/board/analytics responses + the public carousel /blog stay byte-identical; the migration is ADDITIVE (add origin + backfill; NO column drop); the outbox is ADDITIVE (alongside the existing after-commit publish); NO renames. The auto-publish behavior cutover + the destructive embedded-column drop are DEFERRED (documented follow-up; the approval≠release contract is already split in AE-0111). Follow `docs/architecture/module-conventions.md` + the modules/editorial+presentation pattern; reuse the platform UoW, the QA-guardian gates, and the AE-0103/0112/0122 import-contract + ratchet pattern; compose via DI at the edge (no get_container in module code). publishing is invoked BY editorial/presentation via the facade (acyclic; publishing imports no editorial/presentation internals). Precondition: Phase 5 (PR #19) merged. The checkpoint-drain rule applies to any schema-modifying migration (Phase 6's is additive ⇒ no drain needed).

## Acceptance Criteria

- [ ] THE epic SHALL be Done only when AE-0124..0132 are all Done/merged
- [ ] Publishing/blog/distribution SHALL be behind module facades; routes thin adapters; output byte-identical (AE-0125 diff=0)
- [ ] THE BlogPost aggregate SHALL gain an origin field and be backfilled additively from carousel blog (no second representation; no column drop)
- [ ] A transactional outbox SHALL deliver release/workflow events durably (additive; payloads identical)
- [ ] publishing SHALL be invoked by editorial/presentation via the facade only (acyclic; publishing imports no editorial/presentation internals)
- [ ] THE deferred auto-publish cutover + embedded-column drop SHALL be explicitly documented (AE-0132); gates.sh + check-integrity green; publishing contracts KEPT; baseline ratcheted or held

## Gherkin Scenarios

Not applicable — epic tracker; behavior verified by the AE-0125 safety net.

## Delta

### ADDED

- docs/plans/phase-6-publishing-blog-distribution.md (this epic)

### MODIFIED

- `.agent/` board state

### REMOVED

- None

## Affected Areas

- Backend: none
- Frontend: none (Phase 7)
- Database: none (additive-only if any)
- API: none
- Tests: contract/behavior tests
- Docs: references conventions
- Prompts/LLM: none
- Observability: none
- Deployment: none

## Dependencies

- Blocks: —
- Blocked by: None (tracks AE-0124-0132)
- Related: AE-0111, AE-0114, AE-0122, ADR-0009

## Implementation Plan

1. Wave A: AE-0124, AE-0125, AE-0126.
2. Wave B: AE-0127, AE-0130.
3. Wave C: AE-0128, AE-0129.
4. Wave D: AE-0131.
5. Wave E: AE-0132.

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
