# AE-0423 — Blog document model (blog.v2) + one-shot cutover + public render (B)

Status: Done
Tier: T2
Priority: P1
Type: Feature
Area: Cross-cutting
Owner: Claude (worker)
Agent Lane: architect → developer → qa → release
Branch: feat/ae-0423-blog-document-model
Kanban Card: PR #145
Created: 2026-10-18
Updated: 2026-10-19

## Goal

Make `blog_posts.content` a versioned, section-structured document (`blog.v2`) with a cover and
per-section images, cut existing v1 rows over in one shot with an idempotent backend command, and
render v2 on the public page. v2 becomes the **only** persisted shape (no v1 write path), with a
temporary read fail-safe until cutover is verified. This is the foundation for the editor (AE-0424)
and the writer (AE-0425).

## Problem

A blog post is a view over carousel data: `content.markdown` is flat markdown and images are injected
at read time from carousel design (`design_token_utils.py:216-221,280`), so the post cannot own
per-section images, cannot be reordered safely, renders a duplicate H1 (F-08) and empty alts (F-07).
There is no versioned shape and no migration path (ADR-0006 but no `schema`). Design and rationale:
ADR-0025 and `docs/architecture/blog-post-document-model.md`.

## Scope

- Backend: the `blog.v2` shape (cover, ordered sections with stable ids, `translations.en`,
  `quality`); a strict `parse_blog_content` (v2 only, raises on anything else); `BlogDocumentService`
  (validate + keep `featured_image_url` synced with `cover.url`); a `BlogPostDocument` Pydantic model;
  a one-shot, idempotent **backend command** v1 → v2 (`--dry-run` / `--apply` / `--verify` /
  `--rollback`) run as an explicit deploy step; **no Alembic revision**.
- Frontend: a mirrored `parse-blog-content` helper (v2 only); the public page renders v2 sections +
  their own images + cover; one H1; non-empty `alt`; **PT/EN content buttons** switch between
  `content` (PT) and `content.translations.en` (EN), falling back to PT when EN is absent (the
  `?lang=pt|en` parameter is already resolved by `resolvePublicBlogView`).
- Public lean read (ADR-0013) unchanged: `content` carries v2 (all fields public-safe).

## Non-Goals

- The editor UI (AE-0424), the writer/quality gate and image generation (AE-0425).
- Owner photo upload (`source: "upload"` reserved only).
- Removing the `blog_image_map` **field** from the carousel design payload (AE-0428); this ticket
  only stops reading it.
- The review/schedule UI (AE-0424); the status columns already exist.

## Acceptance Criteria

- [x] AC1: `content.schema == "blog.v2"` documents parse to cover + ordered sections (backend and
      frontend helpers). Anything else is rejected — `parse_blog_content` raises
      `InvalidBlogDocumentError`; it never coerces a legacy string into a section.
- [x] AC2: The cutover converts every v1 row in place: splits the PT markdown **and every string
      value in `content.translations`** (`content.translations` is `dict[str, str]`, e.g.
      `{"en": "..."}`) on `^## ` **outside fenced code blocks**, strips a leading `# <title>`, drops
      an empty lede chunk, assigns unique `sec_<uuid4>` ids, sets `cover=null` / `image=null` /
      `quality=null`, and rewrites `content` to the v2 object. Each translation becomes
      `{"schema":"blog.v2","cover":null,"sections":[...],"quality":null}`; non-string translation
      entries are dropped (never `str(dict)`). Section bodies are stored **raw** (no
      `sanitize_display_input` during cutover); non-markdown content becomes an empty section; every
      document ends with >= 1 section. Oversized sections are reported for AE-0426, not truncated.
- [x] AC3: The cutover is idempotent (second `--apply` is a no-op); `--rollback` re-joins
      `## {heading}\n\n{body_md}` and a round-trip test asserts **section body bytes are identical**
      (headings normalize to `## `; the title H1 is not restored). `--rollback` reconstructs both
      `markdown` and each `translations[lang]` string; run it from the new image **before** reverting
      the app code. There is no Alembic revision and no dependency on Alembic heads/stamp.
- [x] AC4: `featured_image_url` stays identical to `cover.url` after any save that changes the
      cover (write-through, one transaction); the cutover sets `featured_image_url = NULL`
      whenever it sets `cover = null`, so the invariant holds from the first v2 row. A null cover is
      allowed at publish: cards/OG use a deterministic fallback (never a carousel slide), covered by
      a test.
- [x] AC5: The public page renders `cover` (or a neutral default), each section's `heading`,
      `body_md` and its own `image` with the stored non-empty `alt`; it never emits a
      `/slide-images/` URL and never reads carousel design for images. **The public read path never
      calls `fetchBlogWithDesign` / `GET /api/carousels/{id}/blog` for content**: the `fromCarousel`
      branch and the legacy `/blog/{project_id}` content fallback in
      `frontend/src/lib/public-blog.ts` are removed. A carousel-origin post with no v2 `blog_posts`
      row returns 404 (it does not resurrect v1 markdown).
- [x] AC6: `--verify` asserts **zero non-v2 rows** (top-level and every translation value) and exits
      non-zero otherwise; the deploy runs
      `--apply --verify` between Postgres-up and full-stack-up; on failure it still brings the stack
      up and fails the job afterwards (review fix: never abort with the stack down). `--verify` uses
      the strict `parse_blog_content`. A non-v2 row is a deploy error to fix, not a supported
      persisted shape. Until cutover runs, the
      **read** path catches `InvalidBlogDocumentError` for a legacy-markdown row and synthesizes a
      text-only v2 document in memory (`cover/images = null`, `quality = null`), emits
      `blog_v2_non_migrated_rows`, never 500s, and never reads carousel slides. Writes stay strict
      (the editor surfaces the error; AE-0424 adds a clear “migration pending” banner). This adapter
      is temporary and is removed in AE-0428.
- [x] AC7: `image.alt` is rejected when empty on write (422); sections require unique ids and at
      least one non-empty `body_md` to publish.
- [x] AC8: Public PT/EN buttons switch the rendered content between `content` and
      `content.translations.en`; a missing EN translation renders PT (never 404); the switch does not
      require the next-intl UI locale to change.
- [x] AC9: The public renderer never consults `blog_image_map`; the payload may still carry the key
      until AE-0428, and the page ignores it. (The assertion that the key is gone from the design
      payload belongs to AE-0428, which owns its deletion.)
- [x] AC10: The public payload is a projection: `quality`, `image.prompt`, `image.model` and
      generation metadata are absent (contract test); `translations.en.quality` is editor-only too.
- [x] AC11: The command supports `--dry-run` (per-row PT/translation counts + oversized flags, no
      writes), `--apply` (batched, one transaction per batch, `pg_advisory_xact_lock`), `--verify`
      (standalone-safe zero-non-v2 gate, including translations) and `--rollback`; a second
      `--apply` changes nothing.
- [x] AC12: `deploy.yml` runs the command with the freshly built backend image **after** Postgres is
      healthy and **before** the full stack is brought up; there is no old/new app overlap and no
      Alembic step. A non-zero exit is captured, `up -d` always runs, and the job fails afterwards
      (never aborts with the stack down). The same command is safe for
      the operator to re-run ad hoc.


## Gherkin Scenarios

- `backend/tests/features/blog_sections_ae0423.feature` (model, cutover, fail-safe, projection sync).
- `frontend/tests/features/blog_sections_ae0423.feature` (public v2 render).
- Scenario list: parse v2; non-v2 rejected; migrate in place (fence-safe, raw body, no `str(dict)`);
  migrate idempotent; `--rollback` re-join body-byte-identical; migrate PT + EN translation;
  non-string translation dropped; migrate H1-stub; `featured_image_url` sync + null-cover fallback;
  render v2 section image + alt; no `/slide-images/`; public read never fetches carousel blog
  markdown; carousel-origin post with no v2 row → 404; empty-alt rejected; `--verify` zero non-v2
  rows + non-zero on a seeded bad row; read fail-safe for a non-migrated row; deploy ordering;
  public projection excludes quality/prompt/model; PT/EN content switch with PT fallback.

## Delta

### ADDED

- `backend/src/rag_backend/domain/models/blog_document.py` (`BlogDocument`, `BlogSection`,
  `BlogImage`), `application/services/blog/blog_document_service.py`, strict `parse_blog_content`
  helper, constants (`BLOG_SCHEMA_V2`, `BLOG_SECTION_MAX_CHARS`).
- `backend/src/rag_backend/scripts/blog_v1_to_v2.py` (`--dry-run` / `--apply` / `--verify` /
  `--rollback`) + tests; no Alembic revision.
- Read fail-safe in the blog document service/projection + `blog_v2_non_migrated_rows` metric.
- `frontend/src/modules/publishing/blog/lib/parse-blog-content.ts` + types.
- Feature specs above.

### MODIFIED

- `BlogPostResponse`/`BlogPostUpdate` validation path (v2 accepted in `content`).
- Public renderer (`blog-post-content.tsx`) and `frontend/src/app/(public)/blog/[id]/page.tsx`.

### REMOVED

- The v1 read path: any `parse_blog_content` v1 branch, legacy markdown handling in the renderer,
  and the `content.legacy_markdown` field (never introduced).


## Affected Areas

- Backend: domain models, application service, cutover command, API schema validation
- Frontend: publishing blog lib + public renderer
- Database: **data cutover** on `blog_posts.content` (no schema change)
- API: `content` shape (v2), no new endpoint
- Tests: backend unit + cutover + feature; frontend unit + feature
- Docs: ADR-0025, architecture companion
- Prompts/LLM: none
- Observability: cutover logs (rows/languages migrated, oversized), `blog_v2_non_migrated_rows`
- Deployment: explicit one-shot step in `.github/workflows/deploy.yml` after Postgres health and
  before `up -d`; no Alembic dependency; a non-zero exit never blocks `up -d` and fails the job after

## Dependencies

- Blocks: AE-0424, AE-0425, AE-0426.
- Blocked by: AE-0422 (removes the carousel→blog dual-write; without it a carousel save can
  re-publish or overwrite the migrated document).
- Related: ADR-0006, ADR-0012, ADR-0025.

## Implementation Plan

1. Feature specs first (backend + frontend).
2. Domain model + strict parse helper + `BlogDocumentService` + unit tests.
3. `blog_v1_to_v2` command (PT + translations) + idempotent/rollback/verify tests; wire the explicit
   deploy step; add the temporary read fail-safe + metric.
4. Public renderer v2 (no legacy branch) + tests.
5. Gates: `bash scripts/ci/gates.sh backend` (with `DATABASE_URL`) and `frontend`.

## QA Checklist

- [ ] Security reviewed (no HTML injection; alt/URLs validated)
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested (empty content, H1-only, malformed JSONB)
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-10-18 16:30

Ticket created from the AE-0422 plan (ADR-0025, wave B).

### 2026-10-19 (worker)

- Backend done: `BlogDocument` model + strict `parse_blog_content`, fence-aware
  splitter/re-joiner, `BlogDocumentService` (strict writes, cover projection, publish
  guard, temporary read fail-safe with deterministic ids + `blog_v2_non_migrated_rows`),
  public projection, cutover runner + `python -m rag_backend.scripts.blog_v1_to_v2`,
  deploy step in `deploy.yml`, API wiring (create/update/get/publish/public/restore/
  generate-image).
- Verified the CLI end to end against a real Postgres 16: dry-run, apply+verify,
  idempotent re-apply, rollback, verify exit 1, re-apply.
- Worktree moved to `~/projects/alter-ego-ae0423` after Orca wiped `~/orca/workspaces/`
  twice mid-run (work restored from the session, then committed/pushed per increment).

## Files Touched

- Backend (new): `domain/constants/blog_document.py`, `domain/models/blog_document.py`,
  `domain/models/blog_document_split.py`, `application/services/blog/{blog_document_service,blog_public_projection}.py`,
  `infrastructure/database/blog_v2_cutover.py`, `scripts/blog_v1_to_v2.py`, `api/dependencies/blog_document.py`.
- Backend (modified): `api/routes/{blog_post,blog_post_workflow,blog_post_versions,blog_post_ai}.py`,
  `api/schemas/public_blog_post.py`; `.github/workflows/deploy.yml` (cutover step).
- Frontend (new): `schemas/blog-document.ts`, `modules/publishing/blog/lib/parse-blog-content.ts`,
  `public-post/{blog-language-switch,section-markdown-components}.tsx`.
- Frontend (modified): `lib/public-blog.ts`, `lib/public-blog-cards.ts`, `lib/server-fetch.ts`
  (`fetchBlogWithDesign` → theme-only `fetchCarouselDesign`), `app/(public)/blog/[id]/page.tsx`,
  `public-post/{blog-post-content,blog-post-hero,types}.tsx`, `modules/publishing/index.ts`, i18n `blog.contentLanguage*`.
- Tests: see Test Evidence; specs `public-blog-detail.feature`, `carousel_editorial_consolidation.feature`
  updated for the retired `/blog/{project_id}` path (superseded notes, not deleted).

## Test Evidence

- Backend full gate run (after rebasing onto the ae-0422 hidden-post fix, live Postgres): `GATES_JSON: {"pass":22,"fail":0,"skip":0,"results":[{"gate":"backend:format","status":"PASS"},{"gate":"backend:lint","status":"PASS"},{"gate":"backend:lint-diff","status":"PASS"},{"gate":"backend:blanket-ignore","status":"PASS"},{"gate":"backend:strict-diff","status":"PASS"},{"gate":"backend:type","status":"PASS"},{"gate":"backend:imports","status":"PASS"},{"gate":"backend:arch-ratchet","status":"PASS"},{"gate":"backend:docstrings","status":"PASS"},{"gate":"backend:dead-code","status":"PASS"},{"gate":"backend:inline-prompts","status":"PASS"},{"gate":"backend:redis-factory","status":"PASS"},{"gate":"backend:autopilot-env","status":"PASS"},{"gate":"backend:healthcheck-loopback","status":"PASS"},{"gate":"backend:bandit","status":"PASS"},{"gate":"backend:pip-audit","status":"PASS"},{"gate":"backend:integrity","status":"PASS"},{"gate":"backend:test","status":"PASS"},{"gate":"backend:diff-cover","status":"PASS"},{"gate":"backend:migrations","status":"PASS"},{"gate":"backend:schema-drift","status":"PASS"},{"gate":"backend:mutation","status":"PASS"}]}`
- Frontend full gate run (after the review fixes): `GATES_JSON: {"pass":17,"fail":0,"skip":0,"results":[{"gate":"frontend:lint","status":"PASS"},{"gate":"frontend:lint-changed","status":"PASS"},{"gate":"frontend:component-types","status":"PASS"},{"gate":"frontend:duplication","status":"PASS"},{"gate":"frontend:dead-code","status":"PASS"},{"gate":"frontend:typecheck","status":"PASS"},{"gate":"frontend:build","status":"PASS"},{"gate":"frontend:legacy-guard","status":"PASS"},{"gate":"frontend:legacy-inventory","status":"PASS"},{"gate":"frontend:format","status":"PASS"},{"gate":"frontend:security","status":"PASS"},{"gate":"frontend:integrity","status":"PASS"},{"gate":"frontend:test","status":"PASS"},{"gate":"frontend:schema-drift","status":"PASS"},{"gate":"frontend:duplication-tests","status":"PASS"},{"gate":"frontend:dead-files","status":"PASS"},{"gate":"frontend:mutation","status":"PASS"}]}`
- Cutover CLI exercised end to end against a real Postgres 16 (see .agent/reports/AE-0423.dev-summary.md).

## QA Report

Pending.

## Decision Log

- **One-shot command, not Alembic.** `content` stays JSONB; only rows are rewritten (no DDL).
  `deploy.yml:255-262` disables migrate-on-deploy because prod was never stamped and the chain had
  two heads; coupling this rewrite to the AE-0207 head/stamp reconcile would add unrelated risk.
  The command is explicit, operator-runnable, idempotent and independent of Alembic state.
- **Explicit deploy ordering.** Build → `down` (no old/new overlap) → Postgres → `--apply --verify`
  → `up -d`. A failed cutover is captured, the stack still comes up (read fail-safe) and the job
  fails afterwards; `deploy.yml` owns the step.
- **Temporary read fail-safe.** A cutover that has not run must not 500 the public blog. Reads adapt
  legacy markdown in memory; writes stay strict; AE-0428 removes the adapter after prod `--verify`.
- **Translations are migrated.** `content.translations` is `dict[str, str]`; each string gets the
  same fence-aware splitter as PT, producing a full v2 document per language.
- **Keep `featured_image_url`.** It is a public allow-listed column read by cards/OG; it becomes a
  synced projection of `cover.url` rather than being removed.
- **No `legacy_markdown`, no v1 persisted read path.** The owner chose "refactor over keeping old
  slop": cut over once, then drop the old shape from code. `--rollback` re-joins sections for a code
  rollback; the parser and renderer stay v2-only, and the temporary service-level read fail-safe is
  not a dual-shape renderer branch.
- **No images in the cutover.** v1 images were never stored (read-time injection), so there is
  nothing to carry.

### Implementation decisions (worker, 2026-10-19)

- **Review fixes (orchestrator code review of PR #145):**
  1. The deploy step never aborts with the stack down: the exit code is captured, `up -d` always
     runs, and the job fails at the end (`deploy.yml`, ADR-0025 and the architecture doc updated).
  2. `--verify` uses the strict `parse_blog_content`; `--apply` and the read fail-safe repair a
     v2-marked row by dropping only the translations that fail the parse (PT is never blanked).
  3. Blank translation strings are not migrated, and `resolveBlogLanguage` falls back to PT when a
     translation has no non-empty section.
  4. `--apply` rewrites every `version_history[*].snapshot` (and `--rollback` reverses it), so
     pre-cutover versions stay restorable under strict writes. Done in the cutover only; no change
     to `blog_post_versions.py` (AE-0424 owns it).
  5. A cleared `featured_image_url` is stashed in `ai_generation_metadata.blog_v2_cutover` and
     restored by `--rollback` when no cover was set since (a newer cover wins).
  Low: a fence line with an info string no longer closes an open fence (CommonMark).
- **Rebase onto the AE-0422 hidden-post 404 fix:** `blog_post_hide.py` (AE-0422) logged %-style
  args through structlog, which raises once the app configured structlog (order-dependent test
  failure). Switched to key/value logging with a regression test that fails on the old call.

- **Structural vs write-only rules.** `parse_blog_content` (every read and write) enforces the
  shape: `schema == "blog.v2"`, non-blank `image.alt`, `https:`/same-origin image URLs, unique
  section ids (`^sec_[A-Za-z0-9_-]{1,64}$`), 2-letter translation keys, no unknown keys.
  `BlogDocumentService.validate_for_write` adds the write-only rules: `body_md <=
  BLOG_SECTION_MAX_CHARS` (20 000), heading `<= 200` chars and not starting with `#` (a `#`
  inside, e.g. "C# tips", is fine), >= 1 section unless `generation.status == "in_progress"`
  (also per translation). This keeps an oversized migrated row readable (flagged for AE-0426)
  while the editor cannot save a new oversized section.
- **Heading-only chunks are kept.** The plan's pseudo-code skipped every empty-body chunk; that
  would silently drop a `## Heading` with no body. Only the empty lede (no heading, blank body)
  is dropped; a headed chunk with an empty body becomes a section with `body_md == ""`.
- **Body bytes.** A section body is the raw text after its heading line minus the surrounding
  newlines (`strip("\r\n")`); `--rollback` re-joins `## {heading}\n\n{body_md}` (lede without a
  heading) with `\n\n` between sections, so section bodies round-trip byte-identically.
- **Partial rows.** A top-level v2 row whose translations are not all v2 keeps its PT document;
  only the stray translation values are converted (strings) or dropped (anything else).
- **`featured_image_url` is never client-writable.** PUT/POST derive it from `content.cover`;
  a client-sent `featured_image_url` is ignored. The legacy `generate-image` route now writes
  `content.cover` through the service (422 before any image spend if the row is not v2; 502 if
  the provider URL is not publishable) so the projection invariant holds on every path.
- **Create.** An empty `content` becomes a fresh valid document (one empty lede section); any
  non-empty non-v2 `content` is a 422. **Restore-version** validates the snapshot as a write
  (a v1 snapshot is a 422).
- **Publish guard.** `POST /publish` requires a v2 document with >= 1 non-empty section (422
  `blog_document_not_publishable`); a null cover is allowed. The scheduled-publish sweep is not
  changed here (AE-0424 owns review/schedule).
- **Read fail-safe ids are deterministic** (`uuid5(post_id:n)`), so repeated reads of the same
  non-migrated row are byte-identical (found via the existing "editor gets the anonymous
  payload byte-identical" test).
- **Cutover keeps `updated_at`** (a data rewrite is not an edit) and does not bump
  `lock_version`. Its report lists every cleared `featured_image_url` so a standalone post's old
  image URL stays recoverable from the deploy log.
- **422 detail format.** `"<code>"` or `"<code>: <message>"`; AE-0424 keys its "migration
  pending" banner on the `blog_document_not_v2` / `invalid_blog_document` prefix.
- **Body sanitization at write is not added here.** `sanitize_display_input` strips `( ) < >`,
  which would break every markdown link; rendering stays behind the react-markdown allow-list.
  AE-0424 decides the editor's write-boundary sanitization.
- **Pre-existing defect found (not fixed here, AE-0424 owns versions):** `restore-version`
  appends a dict to `version_history` while `BlogPostResponse.version_history` is `list[str]`,
  so a successful restore 500s on response validation.


## Risk & Size

- **Risk:** Medium — one-shot data cutover; mitigated by dry-run, idempotency, rollback, the
  zero-non-v2 verify gate and the read fail-safe.
- **Size:** M

## Blockers

None.

## Final Summary

**Merged and closed (orchestrator, 2026-10-20).** Merged #145 together with #147 (b20a12d, 2026-10-19). Prod: cutover ran in the deploy, changed=30; `--verify` scanned=30 non_v2=0. Backup before cutover: droplet /root/backups/blog_posts-pre-ae0423-20261019T174616Z.sql.gz.
