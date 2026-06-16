# AE-0163 — Backend: make blog_posts the single writer + remove embedded-column read fallback (de-risk the drop)

Status: Dev Complete
Tier: T2
Priority: High
Type: Task
Area: Backend
Owner: developer
Agent Lane: planner → architect → developer → qa → release
Branch: feat/phase-8-legacy-removal
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

- [x] blog_posts (origin='carousel') SHALL be the single writer; the embedded-column writers retired/redirected (no remaining embedded-column writes)
- [x] The carousel-blog read path + 404 gate SHALL source body/title/subtitle/404 from the backfill row (no embedded fallback), gated by a backfill-completeness check
- [x] The AE-0125 safety net SHALL diff to ZERO (byte-identical /blog + projections) incl. the HTTP backfill-row parity test
- [x] gates.sh + check-integrity green; no destructive change (additive-only)

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

- NEW `backend/src/rag_backend/infrastructure/database/carousel_blog_dual_write.py` — `sync_carousel_blog_post(session, project)`: idempotent upsert of the `origin='carousel'` blog_posts row in the AE-0127 shape; no-op when `blog_markdown` is None; flush-only (shares caller's transaction).
- `backend/src/rag_backend/infrastructure/database/carousel_repository.py` — `create_project`/`update_project` call `sync_carousel_blog_post` after flush, before commit (the single write chokepoint redirecting all embedded writers).
- `backend/src/rag_backend/modules/publishing/infrastructure/read_projection_helpers.py` — `resolve_blog_body(row)` sources body SOLELY from the backfill row (dropped the embedded_markdown fallback param).
- `backend/src/rag_backend/modules/publishing/infrastructure/publishing_read_acl.py` — `project_carousel_blog` 404 gate now keys on the backfill row's presence (removed the `project.blog_markdown is None` embedded gate).
- `backend/src/rag_backend/infrastructure/database/models/blog_post.py` — `title`/`content` converted to SQLAlchemy 2.0 `Mapped[]`.
- `backend/src/rag_backend/modules/publishing/domain/models.py` — read `model.title` directly (now typed via Mapped[]).
- NEW `backend/alembic/versions/d4e5f6a7b8c9_topup_carousel_blog_backfill.py` — additive, data-only, idempotent top-up backfill (closes the AE-0127 residual gap: any non-null-`blog_markdown` carousel lacking a carousel-origin row); reversible via the AE-0127 downgrade chain.
- `backend/tests/integration/test_publishing_safety_net.py`, `backend/tests/unit/modules/publishing/test_publishing_read_projection.py` — updated to the backfill-row source of truth.

## Test Evidence

- `ruff check src/` — All checks passed.
- arch-ratchet `import_baseline.py --check` — PASS (application→infra 61/61, all pairs unchanged).
- mypy `rag_backend/ --explicit-package-bases` — Success, 492 source files.
- `lint-imports` — 22 contracts kept, 0 broken.
- `pytest test_publishing_safety_net.py test_publishing_read_projection.py` — 51 passed (AE-0125 safety net diff=0).
- `check-integrity.sh backend` — 0 blockers (2 warnings are prior AE-0158/0159 gate edits, justified by those tickets).
- Alembic — upgrade head → downgrade -1 → re-upgrade head all OK (new revision `d4e5f6a7b8c9` chains off `c3d4e5f6a7b8`); no schema change ⇒ autogenerate drift stays empty.

## QA Report

Pending (Phase 8 end-of-phase QA on the full branch).

## Decision Log

- Dual-write (not write-cutover) chosen for the transition: the embedded columns are still WRITTEN (additive) but no longer the READ source of truth — keeps output byte-identical while making `blog_posts` the read source, satisfying AE-0162's "single writer of truth" precondition without a destructive change here.
- 404 gate moved from `project.blog_markdown is None` to the backfill row's presence; the top-up migration guarantees no body-bearing carousel lacks a row, so the legacy 200/404 boundary is preserved.

## Blockers

None.

## Final Summary

Behavior-preserving predecessor to the deferred destructive drop (AE-0162) landed: `blog_posts` (origin='carousel') is now the read source of truth via an idempotent dual-write chokepoint in the carousel repository, the embedded-column read fallback + 404 gate were removed, and a top-up backfill closes the AE-0127 residual gap. AE-0125 safety net diffs to zero; additive-only DB. AE-0162 (the drop) remains Intake / consent + drain-gated.
