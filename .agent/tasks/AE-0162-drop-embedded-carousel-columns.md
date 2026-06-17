# AE-0162 — Backend: drop embedded carousel blog/distribution columns (DESTRUCTIVE, drain-gated, consent-gated)

Status: Intake
Tier: T2
Class: B
Priority: Low
Type: Task
Area: Backend/DB
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0162-drop-embedded-carousel-columns
Kanban Card: TBD
Created: 2026-06-16
Updated: 2026-06-16

## RE-SCOPED 2026-06-17 (architect research + cold-critic skeptical review)

This ticket originally claimed to drop **all six** embedded columns once AE-0163
was "DONE". Two independent reviews proved that premise **false**: AE-0163's
implementation (`carousel_blog_dual_write.py`) only ever consolidated the blog
**body** (`blog_markdown`/`blog_translations`) into `blog_posts.content`. The four
distribution columns (`caption`, `caption_en`, `linkedin_post_pt`,
`linkedin_post_en`) were never given a canonical home or backfill, and are still
actively read/written. The original AC#1 ("blog_posts is the single writer" of all
six) is therefore unmeetable as written.

**The drop is now SPLIT:**
- **This ticket (AE-0162) = the BLOG-columns slice only** — drop `blog_markdown`
  + `blog_translations`. **Priority lowered to Low**: the consolidation *value*
  (single read source) is already banked by AE-0163; the physical drop is cleanup,
  not risk reduction, and is itself gated on retiring the remaining blog writers.
- **AE-0204** — canonical distribution home for caption/LinkedIn (the real blocker).
- **AE-0205** — drop the distribution columns (blocked by AE-0204).
- **AE-0206** — delete the write-dead `caption_en` column.

## Goal

Drop `blog_markdown` + `blog_translations` from `carousel_projects` once the
remaining blog-column writers are retired and the checkpoint-drain gate is
satisfied. DESTRUCTIVE + consent-gated. (The four distribution columns are out of
scope — see AE-0204/0205/0206.)

## Problem

AE-0127 added `BlogPost.origin` + an additive backfill and AE-0163 made
`blog_posts` the read source of truth for the blog body, but the embedded blog
columns are still **written**: `api/routes/carousels/crud.py` (publish endpoint),
`services/carousel/editorial_distribution_pack.py`,
`services/carousel/nodes/content/core.py`, and the checkpoint sync
(`_DISTRIBUTION_SYNC_FIELDS` includes `blog_markdown`). Critically, the dual-write
itself (`carousel_blog_dual_write.py`) **reads** `project.blog_markdown` to build
the canonical row — so that read-source must be replaced before the column can go.

## Scope

PRECONDITION (writer-retirement, not yet shipped by any ticket): retire the blog
writers above and replace the dual-write's self-read of `blog_markdown` with a
non-column source; remove `blog_markdown`/`blog_translations` from
`_DISTRIBUTION_SYNC_FIELDS`. THEN: verify no live `carousel_workflow` checkpoint
carries `blog_markdown`/`blog_translations` keys (resumed checkpoint would re-write
dropped columns); satisfy the checkpoint-drain rule; verify the prod
`carousel_projects` shape matches the migration's expected pre-state (prod is
create_all-bootstrapped, no Alembic — see memory prod-db-schema-drift); author a
reversible-by-backup destructive Alembic migration dropping the two blog columns;
fresh-DB upgrade + drift check + downgrade verified. Consent-gated + drain-gated.

## Non-Goals

- Not executed without explicit owner consent + satisfied checkpoint-drain + AE-0163 done.
- No drop while a live checkpoint references the old shape, or while any code still reads/writes the embedded columns.
- Not before the merged Phases 0-7 have been observed in production (roadmap: "after production observation").

## Modularization Alignment (2026-06-16)

Phase 8 of the modularization plan (§Phase 8 "Remove legacy layers and adapters") — the final phase, after
Phases 0-7 merged (PRs #15-#21). Removes the temporary migration scaffolding to zero. Class A (safe cleanup) is
behavior-preserving and holds the existing green gates with down-only ratchets; Class B (auto-publish cutover +
destructive column drop) is consent-gated + drain-gated (ADR-0008). See `docs/plans/phase-8-legacy-removal.md`.

## Acceptance Criteria

- [ ] Blog-column WRITERS retired first: `crud.py` publish endpoint,
      `editorial_distribution_pack.py`, `nodes/content/core.py`, and the
      dual-write's self-read of `project.blog_markdown` no longer depend on the
      columns; `blog_markdown`/`blog_translations` removed from
      `_DISTRIBUTION_SYNC_FIELDS`. (Word-boundary grep: no app read/write remains.)
- [ ] No live carousel_workflow checkpoint state SHALL carry
      `blog_markdown`/`blog_translations` keys (verified) — a resumed checkpoint
      must not re-write dropped columns
- [ ] A destructive migration SHALL drop **only** `blog_markdown` +
      `blog_translations`, reversible-by-backup; fresh-DB upgrade +
      empty-autogenerate-drift + downgrade verified; prod pre-state shape verified
      before drop
- [ ] Explicit owner consent + checkpoint-drain SHALL be satisfied first; gates.sh
      + check-integrity green

## Gherkin Scenarios

Not applicable — destructive migration; verified by the AE-0163 byte-identical reads (post-fallback-removal) + fresh-DB upgrade/downgrade/drift tests + the checkpoint-drain gate.

## Dependencies

- Blocks: —
- Blocked by: a blog-column writer-retirement step (not yet ticketed; see Scope) +
  consent + checkpoint-drain
- Related: AE-0163 (read-path consolidation, partial), AE-0204 (distribution home),
  AE-0205 (distribution-column drop), AE-0206 (caption_en delete), AE-0152, AE-0133

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-16

Ticket created by planner (Phase 8 breakdown).

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
