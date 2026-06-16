# Phase 6 — Separate Publishing, Blog, and Distribution (epic plan)

**Planner output.** Source: `.agent/reports/domain-modularization.options.md` §"Phase 6" (lines 1024-1050),
the BlogPost decision (lines 299-303), and the `publishing` module-table row (line 465). Builds on merged
Phases 0-5 (`modules/{knowledge,identity,conversation,editorial,presentation}` live). **Precondition: Phase 5
(PR #19) merged.** Reuses the AE-0081 conventions, `modules/_template`, the `platform/database` UoW, the
QA-guardian gates, and the AE-0103/0112/0122 import-contract + baseline-ratchet pattern.

## Goal

Extract a `publishing` bounded context — public visibility + scheduling, the **one** `BlogPost` aggregate
(`blog_posts`-backed, `origin: carousel | standalone`), distribution (captions/Instagram/LinkedIn/SEO/channel
delivery), public read-model projections, and a **transactional outbox** for release events — behind a public
facade. Editorial/presentation invoke publishing through a port/facade (acyclic).

## ⚠️ Scope decision (CRITICAL — read before validating)

Phase 6 is NOT a pure byte-identical extraction: the roadmap exit gate includes a deliberate **behavior change**
("editorial approval never automatically publishes") and a **destructive migration** (drop the embedded carousel
blog/distribution columns). To preserve the project's behavior-preserving discipline and avoid a destructive,
checkpoint-drain-gated migration inside a behind-facade phase, Phase 6 is scoped to the **safe, additive subset**:

**IN (behavior-preserving + additive-only):**
- Extract publishing/blog/distribution behind module facades (routes become thin adapters; behavior-preserving).
- `BlogPost.origin` field + an **ADDITIVE migration** that BACKFILLS `blog_posts` rows from the carousel
  `blog_markdown`/`blog_translations` (`origin='carousel'`) — **without dropping** the embedded columns (they remain
  the read source of truth during the migration window; additive ⇒ no checkpoint-drain needed, reversible).
- Transactional **outbox** added ADDITIVELY (durable at-least-once) alongside the existing after-commit publish
  (keep current event delivery working; outbox becomes the durable path).
- Public read-model **projections** for the public `/blog` + calendar/board/analytics — output **byte-identical**
  to today.
- Route the existing carousel publish (`crud.py` `is_public=True`) through a publishing-module **release command**
  that does EXACTLY what it does today (contract relocation, no behavior change) — building on the AE-0111
  approval≠release contract split.

**DEFERRED (explicitly out of Phase 6 — documented, follow-up + consent-gated):**
- The actual **auto-publish behavior change** (making approval and public release two distinct user actions) — the
  contract is separated (AE-0111 + the release command) but the cutover stays a follow-up (frontend + behavior).
- The **destructive drop** of the embedded carousel columns (`blog_markdown`/`blog_translations`/`caption*`/
  `linkedin_post_*`) — a later, drain-gated, post-migration-window step once `blog_posts` is the confirmed writer.

This keeps Phase 6 byte-identical + additive + reversible; AE-0132 documents the deferrals + reframes the full roadmap exit gate as post-Phase-6, tracked by **AE-0133** (Intake follow-up). Outbox: the emit routes through the outbox as the SINGLE durable publish path (no double delivery). SEO has no code today (deferred).

## Reality vs. spec (2026-06-15 code scan)

- **Dual blog today:** first-class `BlogPostModel` (`blog_posts`, has project_id FK, NO `origin` field) +
  carousel-embedded `blog_markdown`/`blog_translations` (carousel_projects) served by `/api/carousels/{id}/blog`.
  Distribution columns `caption*`/`linkedin_post_*` are also embedded on carousel_projects.
- **Auto-publish conflation:** `crud.py:publish_carousel` sets `is_public=True` directly (approval+release in one
  route). AE-0111 already split approval≠release at the contract level (editorial `ApprovalPort`/`PublicReleasePort`).
- **Scheduling:** `scheduled_publish_service.py` is BlogPost-only (no carousel scheduling); does not touch is_public.
- **Events:** `workflow_event_service.py` publishes to Redis on SQLAlchemy `after_commit` (the Redis-before-commit
  bug is already fixed). NO outbox table exists — Redis is transport only (no durability/replay).
- **Public reads:** the public carousel `/blog` reads carousel_projects directly; calendar/board/analytics are
  editor-only and read aggregates directly. No projections yet.
- **Migration:** alembic squashed baseline `63eaefa67b8c`; dropping the embedded columns is destructive (deferred).
- **Module table:** `publishing` (Supporting) owns BlogPost + carousel-article projection + visibility + scheduling
  + Instagram/LinkedIn/captions/SEO.

## Ticket breakdown

| ID | Title | Tier | Area | Blocked by |
|----|-------|------|------|------------|
| **AE-0123** | Phase 6 epic: Separate Publishing, Blog, and Distribution | T3 | Cross-cutting | — (tracks 0124-0132) |
| **AE-0124** | Publishing/blog/distribution surface + ownership map + migration/outbox/behavior-change risk analysis | T2 | Docs/Arch | — |
| **AE-0125** | Byte-identical safety net (blog/publish/distribution/calendar/board/analytics responses + public carousel /blog) + Gherkin | T2 | Tests | — |
| **AE-0126** | `modules/publishing/` skeleton + facade + bootstrap + domain (BlogPost aggregate, Publication projection, DistributionChannel, PublishingSchedule) + re-exported ports | T2 | Backend | — |
| **AE-0127** | `BlogPost.origin` field + ADDITIVE migration (backfill blog_posts from carousel blog; no column drop) | T2 | Backend/DB | AE-0124, AE-0126 |
| **AE-0128** | Visibility + scheduling behind publishing ports (incl. standalone blog publish/unpublish/schedule); carousel publish via the release command (behavior-preserving) | T2 | Backend | AE-0125, AE-0126 |
| **AE-0129** | Distribution behind ports (captions/Instagram/LinkedIn channel-delivery adapters) — behavior-preserving | T2 | Backend | AE-0125, AE-0126 |
| **AE-0130** | Transactional outbox (additive) for release/workflow events — durable at-least-once relay | T2 | Backend | AE-0126 |
| **AE-0131** | Public read-model projections (public /blog + calendar/board/analytics) — byte-identical output; blog routes behind facade | T2 | Backend | AE-0125, AE-0126, AE-0127, AE-0128, AE-0129 |
| **AE-0132** | Publishing import contracts + exit gate + baseline ratchet + deferred-cutover docs | T2 | Backend/CI | AE-0128, AE-0129, AE-0130, AE-0131 |

## Suggested order (waves)

- **Wave A (parallel):** AE-0124 (map+risk), AE-0125 (safety net), AE-0126 (publishing skeleton).
- **Wave B (parallel):** AE-0127 (origin + additive migration — needs 0124/0126), AE-0130 (outbox — needs 0126).
- **Wave C (parallel):** AE-0128 (visibility/scheduling/release command — needs 0125/0126), AE-0129 (distribution — needs 0125/0126).
- **Wave D:** AE-0131 (read-model projections + blog routes behind facade — needs 0125/0126/0127/0128).
- **Wave E:** AE-0132 (import contracts + exit gate + ratchet + deferred-cutover docs — needs 0128/0129/0130/0131).

## Risks & guardrails

- **Behavior-preserving (the discipline holds for the IN scope).** AE-0125 snapshots blog/publish/distribution/
  calendar/board/analytics + the public carousel /blog; AE-0128/0129/0131 gated on diff=0. The release command does
  exactly what `crud.py` publish does today (no auto-publish change).
- **Additive migration only (AE-0127).** Add `origin` (default/backfill `carousel` for project-linked rows,
  `standalone` else) + backfill `blog_posts` from the embedded carousel blog; DO NOT drop embedded columns. Additive
  + reversible ⇒ the checkpoint-drain gate does NOT block (no old-shape-breaking change). Fresh-DB upgrade +
  empty-autogenerate-diff drift check must pass.
- **Outbox additive (AE-0130).** Add the outbox table + relay alongside the existing after-commit publish; do not
  remove the current path until the outbox is proven. Idempotent, at-least-once; keep event payloads identical.
- **Acyclic direction.** publishing is invoked BY editorial/presentation (release events, blog projection) via the
  facade; publishing imports no editorial/presentation internals (AE-0132 contract enforces it).
- **Deferred items explicitly documented (AE-0132).** The auto-publish cutover + the destructive column drop are
  named as a follow-up with the contract separation already in place; this is a conscious scope boundary, not a gap.
- **No renames.** `carousel_projects` stays one table; embedded columns remain until the deferred drop.

## Epic exit gate (Phase-6 IN scope)

- Publishing/blog/distribution behind module facades; routes are thin adapters.
- `BlogPost` is the one blog aggregate (`origin` field added; carousel blog backfilled additively; no second
  representation introduced); `CarouselArticle` is a read projection, not a new table.
- Public read routes serve byte-identical output via projections; calendar/board/analytics read projections.
- Transactional outbox delivers release/workflow events durably (additive; payloads identical).
- Visibility + scheduling owned by publishing; the carousel publish flow routed through the release command
  (behavior-preserving; approval≠release contract honored).
- `gates.sh` + `check-integrity` green; `publishing-application-isolation` + `publishing-public-facade` +
  `publishing-no-editorial/presentation` contracts KEPT; baseline ratcheted (or held); module-conventions §13
  documents publishing + the deferred auto-publish cutover + column-drop.

## Handoff

→ `/architect-skill` validate loop (confirm AE-0123-0132 Ready; SCRUTINIZE the scope decision — is the additive/
behavior-preserving subset + documented deferrals the right call, or must the auto-publish cutover / column drop be
in-scope?), then execute Waves A→E with the developer-skill + QA-guardian loop.
