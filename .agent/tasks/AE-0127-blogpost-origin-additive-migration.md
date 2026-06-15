# AE-0127 — BlogPost.origin field + ADDITIVE migration (backfill blog_posts from carousel blog; no column drop)

Status: Ready
Tier: T2
Priority: High
Type: Task
Area: Backend/DB
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0127-blogpost-origin-migration
Kanban Card: TBD
Created: 2026-06-15
Updated: 2026-06-15

## Goal

Add the BlogPost origin field ('carousel'|'standalone') + an ADDITIVE Alembic migration that backfills blog_posts rows from the carousel blog_markdown/translations (origin='carousel') WITHOUT dropping the embedded carousel columns. Reversible; the checkpoint-drain gate does not block (additive). Fresh-DB upgrade + empty-autogenerate-diff drift check hold.

## Problem

There is one BlogPost aggregate per the roadmap decision, but the model lacks an origin field and the carousel-derived blog lives in embedded columns. Phase 6 unifies additively (no destructive drop) so reads stay byte-identical and the migration is reversible.

## Scope

- Add origin (Enum/str 'carousel'|'standalone') to BlogPostModel + entity, default/backfill 'standalone' for existing standalone rows and 'carousel' for project-linked rows.
- Additive Alembic migration chaining on the squashed baseline: add the origin column + backfill blog_posts rows from carousel blog_markdown/blog_translations for completed/public carousels (origin='carousel', project_id set), idempotently.
- Do NOT drop the embedded carousel columns (deferred). Migration is reversible (downgrade drops origin + the backfilled rows it created).
- Verify fresh-DB upgrade + empty-autogenerate-diff drift check; additive ⇒ no checkpoint-drain required (document).

## Non-Goals

- No embedded-column drop (deferred).
- No change to existing blog read/write behavior.
- No auto-publish change.

## Modularization Alignment (2026-06-15)

Phase 6 of the modularization plan (§Phase 6). **Behavior-preserving + additive-only** for the IN scope — blog/publish/distribution/calendar/board/analytics responses + the public carousel /blog stay byte-identical; the migration is ADDITIVE (add origin + backfill; NO column drop); the outbox is ADDITIVE (alongside the existing after-commit publish); NO renames. The auto-publish behavior cutover + the destructive embedded-column drop are DEFERRED (documented follow-up; the approval≠release contract is already split in AE-0111). Follow `docs/architecture/module-conventions.md` + the modules/editorial+presentation pattern; reuse the platform UoW, the QA-guardian gates, and the AE-0103/0112/0122 import-contract + ratchet pattern; compose via DI at the edge (no get_container in module code). publishing is invoked BY editorial/presentation via the facade (acyclic; publishing imports no editorial/presentation internals). Precondition: Phase 5 (PR #19) merged. The checkpoint-drain rule applies to any schema-modifying migration (Phase 6's is additive ⇒ no drain needed).

## Acceptance Criteria

- [ ] BlogPostModel + entity SHALL gain a typed origin field ('carousel'|'standalone') with correct backfill defaults
- [ ] AN additive Alembic migration SHALL chain on the baseline, add origin, and backfill blog_posts from carousel blog idempotently — WITHOUT dropping embedded columns
- [ ] THE migration SHALL be reversible (downgrade removes origin + its backfilled rows) and additive ⇒ NOT gated by checkpoint-drain (documented)
- [ ] WHEN fresh-DB upgrade + autogenerate run THE schema SHALL match models (empty diff) and the drift check SHALL pass
- [ ] WHEN mypy/lint-imports/pytest + the AE-0125 safety net run THEY SHALL pass (existing blog reads byte-identical)

## Gherkin Scenarios

Not applicable — additive migration; verified by the AE-0125 safety net + the drift check.

## Delta

### ADDED

- origin field on BlogPost; additive alembic migration (backfill)

### MODIFIED

- infrastructure/database/models/blog_post.py + the blog entity

### REMOVED

- None (embedded columns retained — deferred)

## Affected Areas

- Backend: publishing module
- Frontend: none (Phase 7)
- Database: additive migration (origin+backfill; outbox table); NO destructive drop
- API: none yet
- Tests: contract/behavior tests
- Docs: references conventions
- Prompts/LLM: none
- Observability: none
- Deployment: none

## Dependencies

- Blocks: AE-0131
- Blocked by: AE-0124, AE-0126
- Related: AE-0123, ADR-0009

## Implementation Plan

1. Add origin to model+entity.
2. Write the additive backfill migration (no drop).
3. Verify fresh-DB upgrade + empty-diff drift; safety net green.

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
