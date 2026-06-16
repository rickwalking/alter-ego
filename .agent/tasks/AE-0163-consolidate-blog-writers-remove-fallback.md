# AE-0163 — Backend: make blog_posts the single writer + remove embedded-column read fallback (de-risk the drop)

Status: Ready
Tier: T2
Priority: High
Type: Task
Area: Backend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0163-consolidate-blog-writers-remove-fallback
Kanban Card: TBD
Created: 2026-06-16
Updated: 2026-06-16

## Goal

Behavior-preserving PREDECESSOR to the destructive drop (AE-0162): make blog_posts the sole writer of carousel-blog/distribution content and convert the read path (resolve_blog_body / project_carousel_blog + the 404 gate) to source the body + 404 signal from the AE-0127 backfill row, NOT from the embedded carousel columns. This is the de-risking step the architect flagged: without it, dropping the columns would break live reads.

## Problem

AE-0162 (drop embedded columns) cannot meet its own 'blog_posts is the single writer' precondition: (1) the embedded columns are still LIVE READS — publishing_read_acl.py + read_projection_helpers.resolve_blog_body fall back per-field to project.blog_markdown and the carousel /blog 404 gate keys unconditionally on project.blog_markdown is None; (2) there are 4+ live WRITERS (crud.py, editorial_distribution_pack.py, nodes/content/core.py, refine_copy.py) plus ORM hydration. Dropping the columns today breaks the projection + 404 semantics.

## Scope

(a) Redirect/retire the embedded-column writers so blog_posts (origin='carousel') becomes the single source of truth (dual-write during transition is acceptable if output stays identical); (b) convert resolve_blog_body + project_carousel_blog + the 404 gate to source body/title/subtitle + the 404 signal from the backfill row (drop the per-field embedded fallback), GATED by a backfill-completeness check (every public/completed carousel has a non-empty origin='carousel' blog_posts row); (c) verify the carousel /blog + projections stay BYTE-IDENTICAL (AE-0125 safety net diff=0). Additive-only DB (no drop here).

## Non-Goals

- No destructive migration here (that is AE-0162, gated on this).
- No behavior/output change — byte-identical reads; this only moves the SOURCE from embedded columns to blog_posts.

## Modularization Alignment (2026-06-16)

Phase 8 of the modularization plan (§Phase 8 "Remove legacy layers and adapters"), after Phases 0-7 merged.
See `docs/plans/phase-8-legacy-removal.md`.

## Acceptance Criteria

- [ ] blog_posts (origin='carousel') SHALL be the single writer; the embedded-column writers retired/redirected (no remaining embedded-column writes)
- [ ] The carousel-blog read path + 404 gate SHALL source body/title/subtitle/404 from the backfill row (no embedded fallback), gated by a backfill-completeness check
- [ ] The AE-0125 safety net SHALL diff to ZERO (byte-identical /blog + projections) incl. the HTTP backfill-row parity test
- [ ] gates.sh + check-integrity green; no destructive change (additive-only)

## Gherkin Scenarios

Not applicable — behavior-preserving refactor; verified by the AE-0125 byte-identical safety net (diff=0) + a backfill-completeness assertion.

## Dependencies

- Blocks: AE-0162
- Blocked by: —
- Related: AE-0152

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-16

Ticket created by planner (Phase 8 architect-validation round-1 fix).

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
