# ADR-011: Canonical Distribution Home for Caption + LinkedIn

## Status

Accepted

## Context

The Instagram **caption** and the **LinkedIn posts** (`linkedin_post_pt`,
`linkedin_post_en`) of a carousel-derived content item lived **only** in the
embedded `carousel_projects` columns. `blog_posts` — the row the publishing
bounded context already reads from for the carousel→blog projection (AE-0127 /
AE-0163) — had no home for them, and the AE-0127 backfill copied **only** the blog
body. These three fields were still actively **read**
(`modules/publishing/domain/models.py` `Publication.caption`,
`carousel_template/html_template.py`, `application/services/linkedin_post_generator.py`,
`application/services/phase5_migration_service.py`) and **written**
(`modules/editorial/infrastructure/carousel_project_write_owner.py`
`_DISTRIBUTION_SYNC_FIELDS`, `application/services/carousel/editorial_distribution_pack.py`,
`application/tools/carousel/refine_copy.py`, the publish endpoint).

An architect research pass plus an independent cold-critic skeptical review
(2026-06-17) confirmed that dropping the embedded columns without first giving
these fields a canonical home would cause silent data loss and a broken
IG/LinkedIn publish. AE-0204 (this decision) establishes that home; the
destructive column drop is deferred to AE-0205.

Distribution ownership is architecturally significant per CLAUDE.md and ADR-009
(single writer, no dual source of truth), so it requires an ADR.

## Decision

Give the three distribution fields a canonical home in a new
**`blog_posts.distribution` JSONB column** with the shape
`{caption, linkedin_post_pt, linkedin_post_en}` on the `origin='carousel'` row,
backfilled from the embedded `carousel_projects` columns.

- **Reads** source the three fields SOLELY from `blog_posts.distribution`. They
  route through a single shared accessor
  (`infrastructure/database/distribution_home.py`): entity-based readers consume a
  carousel project loaded through `PostgresCarouselRepository.get_project_by_id`,
  which overlays the three fields onto the entity from the canonical home; the one
  raw-ORM reader (`phase5_migration_service`) calls the accessor directly. The
  embedded columns have **zero** application readers for these fields.
- **Writes** land in the canonical home via the existing carousel-blog write
  chokepoint (`sync_carousel_blog_post`), which mirrors the embedded copy into
  `blog_posts.distribution` on the same row, in the same transaction. The embedded
  columns are retained as a reversible dual-write mirror during the AE-0205
  transition, but they are no longer a source of truth.
- The **LangGraph checkpoint sync is decoupled**: `caption` / `linkedin_post_pt` /
  `linkedin_post_en` are removed from `_DISTRIBUTION_SYNC_FIELDS`, so a resumed
  `AsyncPostgresSaver` checkpoint can no longer resurrect embedded-column writes
  for fields the canonical home owns (only `blog_markdown` — AE-0163's domain —
  remains synced).

This change is **additive and behavior-preserving**: the byte-identical
caption/LinkedIn output is asserted by the AE-0125 publishing safety net, and a
seeded-violation test (AE-0180 standard) fails if a reader regresses to the
embedded column.

## Decision Drivers

- The three fields need a single canonical home before the embedded columns can be
  dropped (AE-0205) without data loss or a broken publish.
- The publishing read ACL already reads the `origin='carousel'` `blog_posts` row;
  putting distribution on that row lets the ACL read from a row it already loads.
- ADR-006 already establishes JSONB-on-`blog_posts` (`content`) for evolving,
  nested content; `distribution` mirrors that proven pattern.
- ADR-009's single-writer / no-dual-source-of-truth rule requires one canonical
  home and a decoupled checkpoint sync.

## Considered Options

### Option 1: A new `carousel_distribution` table (1:1 with the row)

- **Good:** Normalized; room to grow per-channel distribution metadata.
- **Bad:** Over-built for a 1:1, 4-field payload; adds a table + a join + a second
  writer + its own migration/ownership for the publishing ACL to consume, when the
  ACL already loads the `blog_posts` row.
- **Verdict:** Rejected per the skeptical review — premature normalization.
  Revisit only if multi-channel distribution rows (many channels per item, with
  per-channel state) hit the near roadmap.

### Option 2: JSONB `distribution` column on `blog_posts` (chosen)

- **Good:** Matches the existing `blog_posts.content` JSONB pattern (ADR-006); the
  publishing ACL reads it from the row it already uses; one additive migration; one
  writer (the carousel-blog chokepoint); reversible dual-write during transition.
- **Bad:** JSONB reads are marginally slower than dedicated columns (irrelevant for
  this access pattern); no DB-level schema validation (enforced at the app layer,
  per ADR-006).
- **Verdict:** Accepted — best fit for a 1:1, 4-field payload that the publishing
  context already reads alongside the blog body.

### Option 3: Leave the fields on the embedded carousel columns

- **Bad:** Blocks AE-0205; keeps two representations and a checkpoint-sync source
  of truth, violating ADR-009.
- **Verdict:** Rejected — it is the status quo this ticket exists to remove.

## Consequences

**Good:**

- The embedded `carousel_projects` distribution columns become read-dead (zero
  application readers) and source-of-truth-dead, unblocking the AE-0205 drop.
- One canonical home + one accessor seam; the checkpoint sync can no longer
  resurrect embedded writes.
- The publishing ACL reads distribution from the same row it already loads.

**Bad / costs:**

- A reversible dual-write to the embedded columns remains until AE-0205 ships
  (intentional, to keep the change reversible).
- The repository read overlay loads the carousel-origin `blog_posts` row on every
  `get_project_by_id`; acceptable for the single-tenant, pre-production context
  (ADR-009 §1).

## Related Decisions

- [ADR-006: Use JSONB for Rich Content Documents](0006-use-jsonb-for-rich-content.md)
- [ADR-009: Adopt Domain Modular Monolith](0009-adopt-domain-modular-monolith.md)
  (single writer / no dual source of truth)
- Blocks: AE-0205 (drop the embedded distribution columns).
- Related: AE-0127 / AE-0163 (`origin='carousel'` blog_posts row + dual-write),
  AE-0206 (`caption_en`, out of scope here).

## Tags

#database #postgres #jsonb #publishing #distribution #single-writer
