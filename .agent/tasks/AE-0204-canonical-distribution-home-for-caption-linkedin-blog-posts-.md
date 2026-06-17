# AE-0204 — Canonical distribution home for caption/LinkedIn (blog_posts.distribution JSONB)

Status: Intake
Tier: T3
Priority: High
Type: Refactor
Area: backend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-17
Updated: 2026-06-17

## Goal

Give Instagram **caption** and **LinkedIn posts** a single canonical home so the
embedded `carousel_projects` distribution columns can later be retired (AE-0205)
without data loss. This is the genuine blocker the phase-8 plan assumed AE-0163
had already cleared — it had not.

## Problem

`caption`, `linkedin_post_pt`, `linkedin_post_en` live **only** in the
`carousel_projects` embedded columns. `blog_posts` has no home for them and the
AE-0127 backfill (`b2c3d4e5f6a7`) copied **only** the blog body. They are still
actively READ — `modules/publishing/domain/models.py` `Publication.caption`,
`carousel_template/html_template.py`, `application/services/linkedin_post_generator.py`,
`application/services/phase5_migration_service.py` — and WRITTEN —
`modules/editorial/infrastructure/carousel_project_write_owner.py`
`_DISTRIBUTION_SYNC_FIELDS`, `editorial_distribution_pack.py`,
`tools/carousel/refine_copy.py`. Independently confirmed by an architect research
+ cold-critic skeptical review (2026-06-17). Without a canonical home, dropping
the columns = silent data loss + broken IG/LinkedIn publish.

## Scope

- Add a `blog_posts.distribution` **JSONB** column (mirrors the existing
  `blog_posts.content` JSONB pattern) holding `{caption, linkedin_post_pt,
  linkedin_post_en}` for `origin='carousel'` rows.
- Additive Alembic migration + **backfill** from the embedded columns (this
  backfill CAN run, unlike AE-0127 which had nowhere to put these).
- Dual-write chokepoint so writes land in the new home.
- Migrate every reader to the new home (publishing ACL/`Publication.caption`,
  `html_template`, `linkedin_post_generator`, `phase5_migration_service`).
- **Decouple the LangGraph checkpoint sync**: `_DISTRIBUTION_SYNC_FIELDS` must
  stop writing the embedded ORM attrs (write to the new home, or stop
  checkpointing those state keys) — else a resumed `AsyncPostgresSaver`
  checkpoint resurrects embedded-column writes.
- Verify byte-identical output via the AE-0125 publishing safety net.

## Non-Goals

- Dropping the embedded columns (that is AE-0205, blocked by this).
- `caption_en` (it is write-dead → handled by AE-0206, do not give it a home).
- A separate `carousel_distribution` TABLE: rejected per skeptical review —
  over-built for a 1:1, 4-field payload; the JSON-on-`blog_posts` home matches
  the existing pattern and lets the publishing ACL read from the row it already
  uses. Revisit only if multi-channel distribution rows hit the near roadmap.

## Acceptance Criteria

- [ ] `blog_posts.distribution` JSONB added via additive Alembic migration.
- [ ] Backfill copies `caption`/`linkedin_post_pt`/`linkedin_post_en` for all
      `origin='carousel'` rows; verified non-lossy.
- [ ] All readers source these three fields from `blog_posts.distribution`; a
      word-boundary grep shows **no** application read of the embedded
      `caption`/`linkedin_post_*` columns remains.
- [ ] Checkpoint resume no longer writes the embedded columns (sync decoupled).
- [ ] AE-0125 publishing safety net diff = 0.
- [ ] A seeded test fails if a reader still sources from the embedded column
      (rule-fires, per AE-0180).
- [ ] ADR added (distribution ownership is architecturally significant per
      CLAUDE.md / ADR-0009).

## Gherkin Scenarios

```gherkin
Feature: ...

  Scenario: ...
    Given ...
    When ...
    Then ...
```

## Delta

### ADDED

- ...

### MODIFIED

- ...

### REMOVED

- ...

## Affected Areas

- Backend:
- Frontend:
- Database:
- API:
- Tests:
- Docs:
- Prompts/LLM:
- Observability:
- Deployment:

## Dependencies

- Blocks: AE-0205 (drop distribution columns)
- Blocked by: (none — additive, can start now)
- Related: AE-0162, AE-0163, AE-0127, ADR-0006 (JSONB rich content), ADR-0009
  (modular monolith — single writer, no dual source of truth)

## Implementation Plan

1. ...

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-17 HH:mm

Ticket created.

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
