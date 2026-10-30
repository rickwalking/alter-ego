# ADR-028: Channel-Pluggable Publishing Analytics

## Status

Accepted

## Context

The editorial analytics ("Publicados", the publish-velocity chart) counted only
`blog_posts.published_at`. Carousels published to Instagram — through autopilot
runs or the manual publish route — were invisible, and the analytics page had no
Instagram insights at all. Pedro's analytics decision (TRIAGE Q1, 2026-10-22):
analytics = blog + carousel publishing counts + Instagram insights, built so
LinkedIn (a separate future connector ticket — Pedro creates and authorizes the
LinkedIn app) and TikTok slot in later without another redesign.

Counting is architecturally significant per CLAUDE.md and ADR-009, so the
pluggability seam requires an ADR.

## Decision

Publishing counts are aggregated from a channel counter registry
(`application/services/publishing_channels.py`): each counter lists the publish
events (timestamps) of one channel and `EditorialAnalyticsService` turns them
into per-channel totals and weekly velocity. Adding a channel means adding one
counter to `CHANNEL_COUNTERS` — the aggregation never changes.

- `blog`: `blog_posts.published_at`, scoped to the author.
- `carousel` (Instagram): a carousel counts once when it has an Instagram
  publish record — an autopilot run with `ig_post_id` or a manual-publish
  ledger row with `ig_post_id` (the same source `SqlInsightsStore` uses).
  Publish time is the run's `updated_at` (stamped at the PUBLISHED transition)
  or the manual record's `claimed_at`; both are weekly-bucket approximations.
  A public-release carousel (`is_public`) without an Instagram publish record
  is not counted in this channel.

`GET /api/editorial-analytics` returns `summary.channels` (per-channel totals)
and per-week `channels` maps, with the top-level published counts as
cross-channel sums. The insights side reports connector health in a
`connector` block (`channel`, `configured`, `last_sync_at`, `stale`, `error`)
computed per request from the stored snapshots, the six-hour TTL and the first
Graph refresh error — no schema change, and the same block shape is what a
future LinkedIn/TikTok insights connector returns.

The dead `average_views` field was removed from the analytics summary rather
than rendered (it averaged `view_count` over all posts and nothing displayed
it).

## Consequences

- "Publicados" and the velocity chart include carousels automatically on both
  the dashboard home and `/dashboard/analytics`.
- The velocity chart gains a channel picker; per-channel numbers are also
  rendered as text so the meaning never depends on colour alone.
- The analytics page shows Instagram totals, per-post rows with `fetched_at`,
  and the connector state (name, last sync, error) instead of silent zeros.
- A future channel ships a counter (publishing) plus a `connector` block
  (insights) without touching the aggregation or the page structure.
- Publish-time approximations (`updated_at`/`claimed_at`) are accurate to
  weekly buckets; if exact publish timestamps are ever needed, a
  `published_at` column would require a deploy one-shot (prod runs no
  alembic).
