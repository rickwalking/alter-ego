# AE-0423 — Blog document model (blog.v2) + one-shot cutover + public render (B)

Status: Intake
Tier: T2
Priority: P1
Type: Feature
Area: Cross-cutting
Owner: Unassigned
Agent Lane: architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-10-18
Updated: 2026-10-18

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

- [ ] AC1: `content.schema == "blog.v2"` documents parse to cover + ordered sections (backend and
      frontend helpers). Anything else is rejected — `parse_blog_content` raises
      `InvalidBlogDocumentError`; it never coerces a legacy string into a section.
- [ ] AC2: The cutover converts every v1 row in place: splits the PT markdown **and every string
      value in `content.translations`** (`content.translations` is `dict[str, str]`, e.g.
      `{"en": "..."}`) on `^## ` **outside fenced code blocks**, strips a leading `# <title>`, drops
      an empty lede chunk, assigns unique `sec_<uuid4>` ids, sets `cover=null` / `image=null` /
      `quality=null`, and rewrites `content` to the v2 object. Each translation becomes
      `{"schema":"blog.v2","cover":null,"sections":[...],"quality":null}`; non-string translation
      entries are dropped (never `str(dict)`). Section bodies are stored **raw** (no
      `sanitize_display_input` during cutover); non-markdown content becomes an empty section; every
      document ends with >= 1 section. Oversized sections are reported for AE-0426, not truncated.
- [ ] AC3: The cutover is idempotent (second `--apply` is a no-op); `--rollback` re-joins
      `## {heading}\n\n{body_md}` and a round-trip test asserts **section body bytes are identical**
      (headings normalize to `## `; the title H1 is not restored). `--rollback` reconstructs both
      `markdown` and each `translations[lang]` string; run it from the new image **before** reverting
      the app code. There is no Alembic revision and no dependency on Alembic heads/stamp.
- [ ] AC4: `featured_image_url` stays identical to `cover.url` after any save that changes the
      cover (write-through, one transaction); the cutover sets `featured_image_url = NULL`
      whenever it sets `cover = null`, so the invariant holds from the first v2 row. A null cover is
      allowed at publish: cards/OG use a deterministic fallback (never a carousel slide), covered by
      a test.
- [ ] AC5: The public page renders `cover` (or a neutral default), each section's `heading`,
      `body_md` and its own `image` with the stored non-empty `alt`; it never emits a
      `/slide-images/` URL and never reads carousel design for images. **The public read path never
      calls `fetchBlogWithDesign` / `GET /api/carousels/{id}/blog` for content**: the `fromCarousel`
      branch and the legacy `/blog/{project_id}` content fallback in
      `frontend/src/lib/public-blog.ts` are removed. A carousel-origin post with no v2 `blog_posts`
      row returns 404 (it does not resurrect v1 markdown).
- [ ] AC6: `--verify` asserts **zero non-v2 rows** (top-level and every translation value) and exits
      non-zero otherwise; the deploy runs
      `--apply --verify` between Postgres-up and full-stack-up and aborts before traffic on failure.
      A non-v2 row is a deploy error to fix, not a supported persisted shape. Until cutover runs, the
      **read** path catches `InvalidBlogDocumentError` for a legacy-markdown row and synthesizes a
      text-only v2 document in memory (`cover/images = null`, `quality = null`), emits
      `blog_v2_non_migrated_rows`, never 500s, and never reads carousel slides. Writes stay strict
      (the editor surfaces the error; AE-0424 adds a clear “migration pending” banner). This adapter
      is temporary and is removed in AE-0428.
- [ ] AC7: `image.alt` is rejected when empty on write (422); sections require unique ids and at
      least one non-empty `body_md` to publish.
- [ ] AC8: Public PT/EN buttons switch the rendered content between `content` and
      `content.translations.en`; a missing EN translation renders PT (never 404); the switch does not
      require the next-intl UI locale to change.
- [ ] AC9: The public renderer never consults `blog_image_map`; the payload may still carry the key
      until AE-0428, and the page ignores it. (The assertion that the key is gone from the design
      payload belongs to AE-0428, which owns its deletion.)
- [ ] AC10: The public payload is a projection: `quality`, `image.prompt`, `image.model` and
      generation metadata are absent (contract test); `translations.en.quality` is editor-only too.
- [ ] AC11: The command supports `--dry-run` (per-row PT/translation counts + oversized flags, no
      writes), `--apply` (batched, one transaction per batch, `pg_advisory_xact_lock`), `--verify`
      (standalone-safe zero-non-v2 gate, including translations) and `--rollback`; a second
      `--apply` changes nothing.
- [ ] AC12: `deploy.yml` runs the command with the freshly built backend image **after** Postgres is
      healthy and **before** the full stack is brought up; there is no old/new app overlap and no
      Alembic step. A non-zero exit aborts the deploy before traffic. The same command is safe for
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
  before `up -d`; no Alembic dependency; non-zero `--verify` aborts the deploy

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

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Decision Log

- **One-shot command, not Alembic.** `content` stays JSONB; only rows are rewritten (no DDL).
  `deploy.yml:255-262` disables migrate-on-deploy because prod was never stamped and the chain had
  two heads; coupling this rewrite to the AE-0207 head/stamp reconcile would add unrelated risk.
  The command is explicit, operator-runnable, idempotent and independent of Alembic state.
- **Explicit deploy ordering.** Build → `down` (no old/new overlap) → Postgres → `--apply --verify`
  → `up -d`. A failed verify aborts before traffic; `deploy.yml` owns the step (documented here, not
  edited in this docs-only plan).
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


## Risk & Size

- **Risk:** Medium — one-shot data cutover; mitigated by dry-run, idempotency, rollback, the
  zero-non-v2 verify gate and the read fail-safe.
- **Size:** M

## Blockers

None.

## Final Summary

Pending.
