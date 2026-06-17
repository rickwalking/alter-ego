# AE-0204 — Canonical distribution home for caption/LinkedIn (blog_posts.distribution JSONB)

Status: Dev Complete
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

- [x] `blog_posts.distribution` JSONB added via additive Alembic migration
      (`e5f6a7b8c9d0`, off head `d4e5f6a7b8c9`).
- [x] Backfill copies `caption`/`linkedin_post_pt`/`linkedin_post_en` for all
      `origin='carousel'` rows; verified non-lossy (data + migration tests).
- [x] All readers source these three fields from `blog_posts.distribution` (via the
      carousel-repository read overlay + an injected `DistributionReader` for
      phase5); word-boundary grep shows **no** application read of the embedded
      `caption`/`linkedin_post_*` columns remains.
- [x] Checkpoint resume no longer writes the embedded columns (sync decoupled:
      caption/linkedin removed from `_DISTRIBUTION_SYNC_FIELDS`).
- [x] AE-0125 publishing safety net diff = 0.
- [x] A seeded test fails if a reader still sources from the embedded column
      (rule-fires, AE-0180) — `test_caption_route_reads_from_home_not_embedded_column`.
- [x] ADR added (ADR-011, accepted) + listed in root `CLAUDE.md`.

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

### 2026-06-17 — Developer (Dev Complete)

Implemented the canonical distribution home end-to-end:
- Added `blog_posts.distribution` JSONB + additive migration `e5f6a7b8c9d0` with a
  carousel-origin backfill; migration round-trips clean (upgrade head → empty
  drift → downgrade -1 → re-upgrade; `downgrade base` passes).
- Added a single shared accessor (`distribution_home.py`) + domain key constants and
  a `DistributionReader` Protocol.
- Dual-write at the carousel-blog chokepoint; read via the carousel-repository
  overlay (single seam) so all entity readers source the home; phase5 reads via an
  injected reader (no new app/api→infra import — ratchet stayed flat).
- Decoupled the LangGraph checkpoint sync (removed caption/linkedin from
  `_DISTRIBUTION_SYNC_FIELDS`).
- Added accessor/migration/rule-fires/safety-net tests; updated impacted tests.
- ADR-011 added + linked in root CLAUDE.md.

All 17 backend gates PASS (DB gates ran locally); integrity 0 net-new blockers;
validate_all_tickets OK. See `.agent/reports/AE-0204.dev-summary.md`.

## Files Touched

See `.agent/reports/AE-0204.dev-summary.md` → "Files Changed". Key:
`blog_post.py` (column), `distribution_home.py` (NEW), `domain/constants/distribution.py`
(NEW), `carousel_blog_dual_write.py`, `carousel_repository.py`,
`carousel_project_write_owner.py`, `phase5_migration_service.py`, `admin_migration.py`,
`protocols/repositories.py`, `alembic/versions/e5f6a7b8c9d0_*.py`,
`docs/decisions/0011-canonical-distribution-home.md`, `CLAUDE.md`.

## Test Evidence

```
GATES_JSON: {"pass":17,"fail":0,"skip":0,...}  (format,lint,lint-diff,blanket-ignore,
strict-diff,type,imports,arch-ratchet,docstrings,dead-code,bandit,pip-audit,
integrity,test,diff-cover,migrations,mutation — all PASS)
```
- integrity: 0 net-new blockers.
- New tests: `tests/unit/infrastructure/test_distribution_home.py`,
  `tests/integration/test_distribution_home_migration.py`,
  `tests/integration/test_publishing_safety_net.py::TestDistributionCanonicalHome`
  (dual-write population + AE-0180 rule-fires).
- Migration: upgrade/downgrade/re-upgrade round-trip + backfill correctness verified
  against postgres + sqlite.

## QA Report

Pending QA Agent.

## Decision Log

- **Dual-write (reversible) over single-write**: writers keep the embedded columns;
  the carousel-blog chokepoint mirrors into `blog_posts.distribution` (source of
  truth for reads). Embedded columns read-dead → AE-0205 drop is data-loss-free.
- **JSON-on-`blog_posts` over a new `carousel_distribution` table** (ADR-011):
  matches the `content` JSONB pattern; publishing ACL reads the row it already loads.
- **Reader injection for phase5**: `DistributionReader` Protocol in domain + the
  carousel repo's bound reader injected at the admin edge, to keep the app/api→infra
  import ratchet flat (no suppressions/loosening).

Pending.

## Blockers

None.

## Final Summary

Pending.
