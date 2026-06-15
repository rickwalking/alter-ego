# Publishing / Blog / Distribution Surface Ownership Map (Phase 6)

**Status:** Accepted reference (AE-0124) | **Created:** 2026-06-15 | **Tier:** T2 (Docs/Arch)

**Purpose.** Map the **Phase 6 publishing surface** — the dual blog representation
(`BlogPostModel` **and** the carousel-embedded blog/distribution columns), the
publishing/visibility/scheduling state, and the social distribution copy
(caption / LinkedIn) — to its current writer(s) and reader(s) (`file:line`),
owned-vs-deferred classification. It then specifies the three **additive,
behavior-preserving** designs Phase 6 introduces — the `origin` migration +
backfill (AE-0127), the transactional outbox (AE-0130), and the behavior-preserving
release command (AE-0128) — and the **deferred** items (auto-publish cutover +
destructive column drop, AE-0133; SEO optimizer). This is the roadmap-mandated
prerequisite for **AE-0127 / AE-0128 / AE-0130 / AE-0131**.

> Extends the AE-0105 carousel field map (`docs/architecture/carousel-project-field-ownership.md`,
> §2.6 distribution columns) and the AE-0115 presentation map
> (`docs/architecture/presentation-surface-ownership.md`, §8 "Out of Phase 5 —
> distribution & publishing"). Those maps classified the blog/distribution columns
> as **DEF / OUT (Phase 6)**; this document is the deferred detail they pointed at.
> Paths are relative to `backend/src/rag_backend/` unless prefixed. Phase 6 is
> **behavior-preserving + additive-only** for the IN scope — every blog/publish/
> distribution response + the public carousel `/blog` stays byte-identical; the
> migration is additive (add `origin` + backfill; **NO column drop**); the outbox
> is additive (alongside the existing after-commit publish); **no renames**.

**Sources of truth for columns:**

- `backend/src/rag_backend/infrastructure/database/models/blog_post.py`
  (`BlogPostModel`, lines 20–172) — the standalone/unified blog aggregate.
- `backend/src/rag_backend/infrastructure/database/models/carousel.py`
  (`CarouselProjectModel`, the embedded blog/distribution columns at lines 61–66).

---

## 1. The two blog representations (dual-source today)

Phase 6 inherits a **dual blog representation**:

1. **`BlogPostModel`** (`blog_posts` table) — the standalone editorial blog aggregate
   with its own status/workflow, scheduling, SEO meta fields, engagement counters,
   and optimistic-lock token. **There is NO `origin` column today** — nothing
   distinguishes a carousel-derived post from a hand-authored one (`blog_post.py`
   has no `origin`; verified by enumeration of lines 25–81).
2. **Carousel-embedded distribution columns** on `carousel_projects`
   (`blog_markdown`, `blog_translations`, `caption`, `caption_en`,
   `linkedin_post_pt`, `linkedin_post_en`) — the carousel workflow writes the blog
   body + social copy directly onto the carousel god row. The public carousel
   `/blog` endpoints (`carousels/media.py`) read these embedded columns, **not**
   `blog_posts`.

These two never reconcile today. **AE-0127** unifies them additively: add `origin`
to `BlogPostModel` and one-time backfill `blog_posts` rows from the carousel
embedded columns (`origin='carousel'`) for completed/public carousels. The embedded
columns are **NOT dropped** (deferred to AE-0133) and **remain the authoritative
read source during the migration window** — see §5.

---

## 2. `BlogPostModel` column-by-column ownership map

**Owning-context legend:** `Blog/CRUD` = blog create/update/delete lifecycle;
`Blog/Workflow` = blog editorial workflow (submit/approve/reject/publish/schedule);
`Scheduler` = background scheduled-publish worker; `SEO` = SEO meta fields (no
optimizer today — §7); `Engagement` = view/like counters; `System` = DB-managed.

**Class legend:** **PUB** = publishing-owned (moves behind the publishing facade /
ports in AE-0128/0131); **DEF** = deferred-within-Phase-6 (documented, no extraction
action); **SEO-NP** = SEO field present but **NOT** driven by any optimizer (§7);
**SYS** = DB/system-managed. **⚠ MULTI** = written by >1 writer today.

### 2.1 Identity / lifecycle / status

| Column | Type | Meaning | Writer(s) `file:line` | Reader(s) `file:line` | Class |
|--------|------|---------|------------------------|------------------------|-------|
| `id` | String(36) PK | Blog post UUID | `from_entity` only (`blog_post.py:140`) | all gets/lists | SYS |
| `project_id` | String(36) FK→carousel_projects (SET NULL) | Source carousel (links a carousel-derived post) | `from_entity` (`blog_post.py:141`) | AE-0127 backfill key; AE-0131 projection | PUB |
| `title` | String(255) | Post title | create `blog_post.py:82` (`from_entity`); update via versioned `apply_versioned_update` | list/get; workflow notifications | PUB |
| `slug` | String(255) unique | URL slug | `from_entity` (`blog_post.py:144`); versioned update | list search (`blog_post_repository.py:42`) | PUB |
| `status` | String(50) (default `draft`) | Blog lifecycle (`draft`/`under_review`/`approved`/`published`) | **W-BW** submit `blog_post_workflow.py:117`; approve `:156`; reject `:186`; publish `:249`; unpublish `:309`; **W-SCH** scheduler `scheduled_publish_service.py:56` | list filter (`blog_post_repository.py:35`); scheduler query `:46` | PUB ⚠ |

### 2.2 Content

| Column | Type | Meaning | Writer(s) `file:line` | Class |
|--------|------|---------|------------------------|-------|
| `content` | JSON (default dict) | Rich blog body (JSONB, ADR-006) | `from_entity` `blog_post.py:145`; versioned update | PUB |
| `excerpt` | String(500) null | Short summary | `from_entity` `:146`; versioned update | PUB |
| `featured_image_url` | String(500) null | Hero image URL | `from_entity` `:147`; versioned update | PUB |

### 2.3 Editorial / review

| Column | Type | Meaning | Writer(s) `file:line` | Class |
|--------|------|---------|------------------------|-------|
| `author_id` | String(36) FK→users | Author | create stamp `blog_post.py route :83` (`post.author_id = current_user.id`); `from_entity` `:148` | PUB |
| `reviewer_id` | String(36) FK→users | Assigned reviewer | **W-BW** submit `blog_post_workflow.py:119`; `from_entity` `:149` | PUB ⚠ |
| `editor_comments` | JSON (default list) | Reviewer comments (reject appends) | **W-BW** reject `blog_post_workflow.py:191`; `from_entity` `:150` | PUB ⚠ |
| `version_history` | JSON (default list) | Edit history | `from_entity` `:151`; blog_post_versions routes | PUB |

### 2.4 Sources / AI assistance

| Column | Type | Meaning | Writer(s) `file:line` | Class |
|--------|------|---------|------------------------|-------|
| `sources` | JSON (default list) | Research sources | `from_entity` `:152`; sources routes | PUB |
| `citations` | JSON (default list) | Inline citations | `from_entity` `:153` | PUB |
| `ai_suggestions` | JSON (default list) | AI suggestion payloads | `from_entity` `:154`; blog_post_ai routes | PUB |
| `ai_generation_metadata` | JSON (default dict) | AI provenance (model/provider) | `from_entity` `:155` | PUB (read by disclosure gate `blog_post_workflow.py:236`) |
| `ai_disclosure_label` | String(50) (default `none`) | AI disclosure label | `from_entity` `:156`; read in publish gate `blog_post_workflow.py:240` | PUB |

### 2.5 SEO meta (present; NO optimizer — deferred)

| Column | Type | Meaning | Writer(s) `file:line` | Class |
|--------|------|---------|------------------------|-------|
| `meta_title` | String(255) null | SEO title tag | `from_entity` `blog_post.py:157`; versioned update only | **SEO-NP** |
| `meta_description` | String(500) null | SEO meta description | `from_entity` `:158`; versioned update only | **SEO-NP** |
| `keywords` | JSON (default list) | SEO keywords | `from_entity` `:159` | **SEO-NP** |
| `canonical_url` | String(500) null | Canonical URL | `from_entity` `:160` | **SEO-NP** |

> These four fields exist but are **only** ever set via blog create/update payloads
> (`from_entity` / `apply_versioned_update`). There is **no SEO optimizer** that
> computes or writes them — see §7. `SeoAnalysisService`
> (`application/services/seo_analysis_service.py`) only **scores** readiness
> (read-only); it writes nothing.

### 2.6 Engagement counters

| Column | Type | Meaning | Writer(s) `file:line` | Class |
|--------|------|---------|------------------------|-------|
| `view_count` | Integer (default 0) | Views | `from_entity` `:161` (no incrementer wired today) | DEF |
| `like_count` | Integer (default 0) | Likes | `from_entity` `:162` | DEF |
| `comment_count` | Integer (default 0) | Comments | `from_entity` `:163` (blog_post_comments routes) | DEF |
| `share_count` | Integer (default 0) | Shares | `from_entity` `:164` | DEF |

### 2.7 Timestamps / scheduling / concurrency

| Column | Type | Meaning | Writer(s) `file:line` | Class |
|--------|------|---------|------------------------|-------|
| `created_at` | DateTime | Creation | server_default (`blog_post.py:68`) | SYS |
| `updated_at` | DateTime | Last-modified | server `onupdate` (`:71`) | SYS |
| `submitted_for_review_at` | DateTime null | Submit timestamp | **W-BW** submit `blog_post_workflow.py:118`; cleared on reject `:187`/unpublish `:311` | PUB ⚠ |
| `approved_at` | DateTime null | Approval timestamp | **W-BW** approve `blog_post_workflow.py:157` | PUB |
| `published_at` | DateTime null | Publication timestamp | **W-BW** publish `blog_post_workflow.py:250`; cleared on unpublish `:310`; **W-SCH** scheduler `scheduled_publish_service.py:57` | PUB ⚠ |
| `scheduled_publish_at` | DateTime null | Future publish time | **W-BW** schedule via `scheduled_publish_service.schedule_post:87`; cleared on publish `blog_post_workflow.py:251`; **W-SCH** cleared `scheduled_publish_service.py:58` | PUB ⚠ |
| `lock_version` | Integer (default 1) | Optimistic-lock token | `OptimisticLockService.apply_versioned_update` (CAS) via `blog_post.py route :180` | PUB |

**Blog writers (logical):**

- **W-BR** — blog CRUD route (`api/routes/blog_post.py`): create (`:82–96`), versioned
  update (`:178–209`), delete (`:234`). Persists via `db.add`/`apply_versioned_update`.
- **W-BW** — blog workflow route (`api/routes/blog_post_workflow.py`): submit/approve/
  reject/publish/schedule/unpublish (`:117,156,186,249,309` + schedule `:286`).
- **W-SCH** — scheduled-publish worker (`application/services/scheduled_publish_service.py`):
  `process_due_posts` (`:56–58`, separate session via `session_factory`) + `schedule_post`
  (`:87`).

**Blog readers (NOT writers):** list (`blog_post_repository.list_summaries:27–62`),
get (`blog_post.py:150` → `get_blog_post_for_read`), AI/quality/versions/comments/
sources routes, and the SEO **scorer** (`seo_analysis_service.py`, read-only).

---

## 3. Carousel-embedded blog / distribution columns

These six columns live on `carousel_projects` (the carousel god row) and carry the
carousel-derived blog body + social copy. AE-0105 §2.6 classified them **DEF**;
this is the Phase 6 detail.

| Column | Type (`carousel.py`) | Meaning | Writer(s) `file:line` | Reader(s) `file:line` | Class |
|--------|----------------------|---------|------------------------|------------------------|-------|
| `blog_markdown` | Text null (`:61`) | PT blog body | **W-DP** distribution pack `editorial_distribution_pack.py:105`; **W-CN** content node `nodes/content/core.py:141`; **W-PUB** publish build-if-missing `carousels/crud.py:233`; **W-SY** sync owner `carousel_project_write_owner.py:53`; `update_from_entity` `carousel.py:267` | public `/blog` `media.py:140,143`; AE-0131 projection | PUB ⚠ |
| `blog_translations` | JSON null (`:62`) | Blog body keyed by language | **W-DP** `:106`; **W-CN** `nodes/content/core.py:142`; **W-PUB** `crud.py:234`; `update_from_entity` `carousel.py:268` | `/blog/{lang}` via `project.get_blog(lang)` `media.py:167`; AE-0131 projection | PUB ⚠ |
| `caption` | Text null (`:63`) | PT social caption | **W-DP** `editorial_distribution_pack.py:112`; **W-RC** refine tool `tools/carousel/refine_copy.py:42`; **W-SY** sync owner `carousel_project_write_owner.py:52`; `update_from_entity` `carousel.py:269` | distribution-pack response `editorial_distribution_pack.py:124` | PUB ⚠ |
| `caption_en` | Text null (`:64`) | EN social caption | `update_from_entity` `carousel.py:270` (no active app writer today) | — | DEF |
| `linkedin_post_pt` | Text null (`:65`) | PT LinkedIn post | **W-DP** `editorial_distribution_pack.py:117`; **W-RC** `refine_copy.py:50`; **W-SY** sync owner `carousel_project_write_owner.py:54`; `update_from_entity` `carousel.py:271` | distribution-pack response `:126` | PUB ⚠ |
| `linkedin_post_en` | Text null (`:66`) | EN LinkedIn post | **W-DP** `editorial_distribution_pack.py:119`; **W-RC** `refine_copy.py:58`; **W-SY** sync owner `carousel_project_write_owner.py:55`; `update_from_entity` `carousel.py:272` | distribution-pack response `:127` | PUB ⚠ |

**Embedded-column writers (logical):**

- **W-DP** — distribution pack service (`application/services/carousel/
  editorial_distribution_pack.py:105–121`): the primary authoring path (blog +
  caption + LinkedIn), persisted via `repo.update_project`.
- **W-CN** — content node (`application/services/carousel/nodes/content/core.py:141–142`):
  entity-side blog write during workflow content generation.
- **W-PUB** — carousel publish route (`api/routes/carousels/crud.py:233–238`):
  **build-if-missing** blog at publish time (only when `not project.blog_markdown`).
- **W-SY** — editorial single-write owner sync (`modules/editorial/infrastructure/
  carousel_project_write_owner.py:51–108`, `sync_phase`): re-syncs the four
  `_DISTRIBUTION_SYNC_FIELDS` (`caption`/`blog_markdown`/`linkedin_post_pt`/
  `linkedin_post_en`) from workflow state onto the row for the Kanban board
  (byte-identical to the pre-AE-0107 `_sync_project_phase` body).
- **W-RC** — refine-copy tool (`application/tools/carousel/refine_copy.py:42,50,58`):
  human-driven copy rewrites, persisted via `repository.update_project` (`:43,51,59`).

**Embedded-column reader (public `/blog`):** `api/routes/carousels/media.py`
`get_carousel_blog` (`:138–146`, reads `project.blog_markdown`) and
`get_carousel_blog_i18n` (`:164–197`, reads `project.get_blog(lang)` →
`blog_translations`). These are **public** (gated by `assert_carousel_public`,
`:139,165`) and are the surface AE-0131 turns into a projection (still reading the
embedded columns as the fallback — §5).

---

## 4. Publishing / visibility state (carousel side)

The carousel "publish" path is conflated with **visibility** and **workflow phase**
on the same god row (AE-0105 §2.1/§2.3; reproduced here for the publishing surface):

| Column | Type | Meaning | Writer(s) `file:line` | Class |
|--------|------|---------|------------------------|-------|
| `is_public` | Boolean (default False, `carousel.py:39`) | Public visibility (homepage + carousel `/blog`) | **W-PUB** publish `crud.py:239` (entity) **+** `crud.py:244` (model direct, second commit `:246`); `update_from_entity` `carousel.py:287` | PUB ⚠ |
| `current_phase` | String(50) (`carousel.py:89`) | Workflow phase pointer | **W-PUB** publish stamps `PHASE_PUBLISHED` `crud.py:240,245`; editorial sync owner; migration | (workflow) |
| `workflow_status` | String(50) (`carousel.py:91`) | Approval gate (`approved_for_publish`) | editorial workflow service (AE-0105 §2.3) | (workflow) — **read** as publish precondition `crud.py:175` |

The **publish read** for visibility is `list_carousels` (`crud.py:101–102,107–119`,
anonymous users see only `is_public`) and the public `/blog`/`/design`/image
endpoints (`media.py`, gated by `assert_carousel_public`).

---

## 5. Dual-source read window (AE-0127 / AE-0131)

During the Phase 6 migration window there are **two** stores of the carousel-derived
blog body. The contract for the window:

1. **One-time backfill (AE-0127).** The additive migration copies
   `carousel_projects.blog_markdown` / `blog_translations` into new `blog_posts`
   rows (`origin='carousel'`, `project_id` set) for **completed/public** carousels.
   This runs **once**.
2. **The embedded columns REMAIN the authoritative read source.** Ongoing carousel
   writes (**W-DP / W-CN / W-PUB / W-SY / W-RC**, §3) still land in the **embedded
   columns** until the deferred cutover/drop (AE-0133). The backfill does **not**
   redirect those writes. Therefore the public carousel `/blog` (`media.py:140,167`)
   continues to read the embedded columns.
3. **AE-0131 projections fall back to the embedded columns.** The public-read
   projections read `blog_posts` rows of `origin='carousel'` (backfilled by AE-0127)
   **but fall back to the embedded carousel columns where needed** so the response
   stays **byte-identical** to today. The embedded columns are the source of truth;
   the projection is an additive read path layered over them.
4. **No reconciliation drift handling is in scope.** Because writes still target the
   embedded columns post-backfill, a carousel re-generated after the backfill will
   have fresher embedded data than its `origin='carousel'` `blog_posts` row — which
   is why §3-readers and AE-0131 treat the **embedded columns as authoritative** and
   the `blog_posts` projection row as a fallback/additive view, not the system of
   record, until AE-0133 makes `blog_posts` the single writer.

---

## 6. Phase 6 designs (additive, behavior-preserving)

### 6.1 Additive migration: `origin` + backfill (AE-0127)

**Goal.** Add `BlogPostModel.origin` (`'carousel'` | `'standalone'`) and backfill
`blog_posts` rows from the carousel embedded columns — **additive only**.

- **Schema add.** Add `origin` (String/Enum, NOT NULL, default `'standalone'`) to
  `BlogPostModel` + the blog entity. Existing standalone rows → `'standalone'`;
  project-linked rows (`project_id IS NOT NULL`) → `'carousel'`.
- **Backfill.** For **completed/public** carousels (`status = COMPLETED` and/or
  `is_public = TRUE`) with non-null `blog_markdown`, insert a `blog_posts` row with
  `origin='carousel'`, `project_id` set, `content`/`title`/`slug` derived from the
  carousel blog body + `blog_translations`. **Idempotent** — guarded so a re-run
  inserts no duplicate (e.g. `WHERE NOT EXISTS` on `(project_id, origin='carousel')`).
- **NO column drop.** The embedded `blog_markdown`/`blog_translations`/`caption*`/
  `linkedin_post_*` columns are **kept** (drop deferred to AE-0133). The migration
  is **purely additive** to `carousel_projects` (no change) and adds one column +
  data to `blog_posts`.
- **Reversible.** `downgrade()` drops the `origin` column and deletes the backfilled
  `origin='carousel'` rows (or just drops the column if backfill rows are
  distinguishable), restoring the pre-migration schema.
- **Drift / fresh-DB.** The migration chains on the squashed baseline
  (`alembic/versions/63eaefa67b8c_initial_baseline_schema.py`). A **fresh-DB
  `upgrade head`** must succeed, and an **empty autogenerate diff** (model ↔ schema
  drift check, run in `scripts/ci/gates.sh`) must hold afterwards — so the new
  `origin` column must be present in **both** `BlogPostModel` and the migration.
- **Checkpoint-drain.** Not required — the migration is additive (no destructive
  schema change), so the checkpoint-drain rule does not block it.

### 6.2 Additive transactional outbox — the single durable publish path (AE-0130)

**Today (the durability gap).** `WorkflowEventService.emit`
(`application/services/workflow_event_service.py:60–95`) writes the audit row +
**queues** the stream event in `session.info[SESSION_INFO_PENDING_EVENTS]`
(`:94`). On commit, the SQLAlchemy `after_commit` listener
(`_on_session_commit:155–163`) schedules a **fire-and-forget asyncio task**
(`_schedule_publish:139–152`) that publishes to Redis; **publish failures are logged,
never raised** (`_publish_events:126–136`). If Redis is down (or the process dies)
**after** commit, the event is **lost** — no durability, no replay.

**Design (additive).**

- **Outbox table** — `outbox` (`event_id`, `event_type`, `aggregate_id`,
  `aggregate_type`, `payload`, `metadata`, `created_at`, `published_at`,
  `attempts`). The **emit writes the outbox row IN-TRANSACTION** — `emit` adds the
  outbox row to the **same** `db` session as the state change (next to the existing
  `WorkflowAuditLogModel` write at `:83–93`), so it commits atomically with the
  business write (transactional outbox pattern). No event is durable-recorded unless
  its state change committed, and vice-versa.
- **Relay = the SOLE Redis publisher.** A relay (worker/poller) reads unpublished
  outbox rows (`published_at IS NULL`), publishes them to the **existing** Redis
  stream (`STREAM_CONTENT_EVENTS`), and marks `published_at`/bumps `attempts`. The
  relay is the **single durable publish path**; the current after-commit
  fire-and-forget publisher is **retired into** the relay (the relay becomes the only
  thing that calls `publisher.publish`).
- **At-least-once + idempotent.** The relay delivers **at-least-once** (a crash
  between Redis-publish and the `published_at` mark re-delivers on the next poll).
  `event_id` is stable (`emit` generates it once, `:72`), so **consumers dedupe** on
  `event_id` (idempotent processing per ADR-004 / backend event rules).
- **Identical payloads.** The outbox row stores the **same** `stream_event` dict
  (`:73–82`) that the after-commit path publishes today — the relay publishes
  byte-identical payloads, so consumers see no change.
- **Bounded duplicate-delivery window.** During any transition where **both** the
  legacy after-commit publisher and the new relay are active for the same event,
  delivery may double. This is bounded and safe because (a) consumers already dedupe
  on the stable `event_id`, and (b) the cutover retires the after-commit publisher so
  the relay is the **single** publisher — the only duplicate source is the relay's own
  at-least-once retry (crash before the `published_at` mark), which the `event_id`
  dedupe absorbs. Document this window as "at-most one redundant delivery per event,
  absorbed by `event_id` dedupe."

### 6.3 Behavior-preserving release command (AE-0128)

**Today (the auto-publish conflation).** `publish_carousel`
(`api/routes/carousels/crud.py:163–247`) **directly** sets `is_public = True`
(`:239` entity + `:244` model) and stamps `current_phase = PHASE_PUBLISHED`
(`:240,245`), guarded only by the `workflow_status == approved_for_publish`
precondition (`:175`) + `status == COMPLETED` (`:183`) + artifact health (`:189`).
Visibility (`is_public`), workflow phase, and the build-if-missing blog (`:233–238`)
are all **conflated** in one route handler that reaches straight into the ORM. The
**approval ≠ release** contract is already split at AE-0111 (`workflow_status` is the
approval token, `is_public` is the release flag).

**AE-0128 (behavior-preserving).** Route the `is_public` write (and scheduling)
through a **publishing-module RELEASE command** behind publishing ports + a
publishing ACL/owner (the only publishing code touching the carousel/blog ORM for
these writes). The release command does **EXACTLY** what the route does today —
**same preconditions, still sets `is_public = True`, no auto-publish change** — so
behavior is byte-identical. This builds on the AE-0111 approval≠release split.

**DEFERRED to AE-0133 (NOT in Phase 6):**

1. **Auto-publish cutover.** Making editorial approval and public release two
   **distinct user actions** (approval never auto-publishes) is a **behavior change**
   that needs the Phase-7 frontend + explicit owner consent. AE-0128 keeps the
   current auto-publish-on-approval-then-publish flow; the cutover is tracked by
   AE-0133.
2. **Destructive embedded-column drop.** Dropping `blog_markdown`/`blog_translations`/
   `caption*`/`linkedin_post_*` from `carousel_projects` is **destructive** and
   **checkpoint-drain-gated** (every live LangGraph checkpoint must finish on
   pre-migration code or restart with documented consent), and requires `blog_posts`
   to be the **confirmed single writer** (no remaining embedded-column writers from
   §3). Deferred to AE-0133.

---

## 7. SEO — NOT PRESENT (deferred, out of Phase 6 scope)

`BlogPostModel` carries SEO meta fields (`meta_title`, `meta_description`,
`keywords`, `canonical_url`, §2.5) **but there is no SEO optimizer** in the codebase
today:

- The only SEO code is `application/services/seo_analysis_service.py`
  (`SeoAnalysisService.analyze`) — it **scores** SEO readiness and returns issues
  (read-only); it **never writes** any column.
- The meta fields are **only** populated via blog create/update payloads
  (`from_entity` `blog_post.py:157–160` / `apply_versioned_update`). No service
  computes or auto-fills them.

SEO optimization (auto-generating meta tags / canonical URLs / keyword extraction)
is **DEFERRED, out of Phase 6 scope**. AE-0124..0133 do not introduce it.

---

## 8. Sufficiency for AE-0127 / 0128 / 0130 / 0131 (no unmapped surface)

| Ticket | What it needs | Where it is mapped |
|--------|---------------|--------------------|
| **AE-0127** (origin + backfill) | every `BlogPostModel` column + embedded carousel blog columns + writers; additive migration + drift/reversible contract | §2, §3, §6.1, §5 |
| **AE-0128** (visibility/scheduling/release) | `is_public` + scheduling writers; the auto-publish conflation; behavior-preserving vs deferred | §4, §2.7, §6.3 |
| **AE-0130** (transactional outbox) | the current after-commit publish path; single durable path; at-least-once/idempotent/identical payloads; duplicate window | §6.2 |
| **AE-0131** (read-model projections) | public `/blog` readers; dual-source fallback contract | §3 (readers), §5 |

All `BlogPostModel` columns (32, all of `blog_post.py:25–81`) and all six embedded
carousel distribution columns (`carousel.py:61–66`) + the `is_public`/publish state
are mapped with type, writer(s)/reader(s) `file:line`, and owned-vs-deferred class.
There is **no unmapped publishing/blog/distribution surface**, so AE-0127/0128/0130/
0131 can be scoped from this map.

**Summary counts.** **32 `BlogPostModel` columns** mapped (4 SEO-NP, 4 engagement
DEF, 6 SYS, the rest PUB) · **6 carousel-embedded distribution columns** mapped
(5 with active writers, `caption_en` DEF) · **8 distinct writer surfaces**
(blog: W-BR / W-BW / W-SCH; embedded: W-DP / W-CN / W-PUB / W-SY / W-RC) ·
**publishing-owned vs deferred:** the migration/outbox/release are **owned (Phase 6,
additive + behavior-preserving)**; the **auto-publish cutover + destructive column
drop (AE-0133) and SEO optimizer are DEFERRED**.

---

## 9. References

- BlogPost model: `backend/src/rag_backend/infrastructure/database/models/blog_post.py`
- Carousel model (embedded columns): `backend/src/rag_backend/infrastructure/database/models/carousel.py`
- Workflow event service (current publish path): `backend/src/rag_backend/application/services/workflow_event_service.py`
- Scheduled publish worker: `backend/src/rag_backend/application/services/scheduled_publish_service.py`
- Carousel publish (auto-publish conflation): `backend/src/rag_backend/api/routes/carousels/crud.py`
- Public carousel `/blog`: `backend/src/rag_backend/api/routes/carousels/media.py`
- SEO scorer (read-only, no optimizer): `backend/src/rag_backend/application/services/seo_analysis_service.py`
- AE-0105 carousel field map: `docs/architecture/carousel-project-field-ownership.md`
- AE-0115 presentation map: `docs/architecture/presentation-surface-ownership.md`
- Phase 6 plan: `docs/plans/phase-6-publishing-blog-distribution.md`
- Module conventions: `docs/architecture/module-conventions.md`
- ADR-004 (Event-Driven), ADR-006 (JSONB), ADR-009 (Domain Modular Monolith): `docs/decisions/`
- Tickets: `.agent/tasks/AE-0124` (this map); blocks AE-0127 / AE-0128 / AE-0130 / AE-0131; deferrals tracked by AE-0133; approval≠release split AE-0111.
