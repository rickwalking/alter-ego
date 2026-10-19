# AE-0425 — Blog writer (voice) + GPT images + generation entry points (D)

Status: Dev Complete
Tier: T2
Priority: P1
Type: Feature
Area: Cross-cutting
Owner: Claude (worker)
Agent Lane: architect → developer → qa → release
Branch: feat/ae-0425-blog-writer-voice-images
Kanban Card: PR #146 (base feat/ae-0424-section-editor)
Created: 2026-10-18
Updated: 2026-10-19

## Goal

Generate ONE continuous blog article in the owner's voice from carousel inputs or a standalone topic,
attach a GPT-generated cover and one GPT-generated image per section, and always create a draft.
Give the owner two entry points: "create blog from carousel" and standalone generation.

## Problem

The body is a mechanical join of `long_form_notes` (`blog_composition.py:117-139`) with no persona
applied (F-02), it repeats one source sentence across sections (F-03), there is no standalone
generation or "create from carousel" affordance (F-09), the editor cannot feed a persona (F-11), and
the body has no images of its own. Design: ADR-0025, `docs/architecture/blog-post-document-model.md`.

## Scope

- **Writer** (`agents/blog_writer/` facade + `application/services/blog/blog_generation_service.py`):
  one continuous article from research findings + outline + `long_form_notes`, prompted with the
  persona style guide + `writing_samples[:5]` (`persona_agent.py:87-116`); output = cover prompt +
  ordered sections + `translations.en`. Prompts in `agents/prompts/blog/v1/` (`.md`/`.yaml`, never
  `.py`).
- **Quality gate:** `PersonaAgent.evaluate_match(body)` `overall >= 70` else exactly one rewrite
  pass; deterministic repetition / AI-cliché scan with a banned stock-phrase list kept as data
  (`domain/constants/blog_voice.py`). Store `content.quality` + mirror to
  `ai_generation_metadata.voice_score`.
- **Images:** cover + one image per section via
  `image_provider_registry().resolve(IMAGE_MODEL_OPENAI, IMAGE_STYLE_CINEMATIC)` (`gpt-image-2`);
  prompt template with "no text/words/letters", passed through `sanitize_image_prompt`; the
  provider result is downloaded and **persisted** to the blog-images store, and only the canonical
  CDN/same-origin URL is stored (provider URLs expire and are never persisted); bounded concurrency
  + per-post cost cap; failure leaves `image=null` + `errors[]` and never blocks the draft. **The section count is the carousel's slide count, not a blog-only maximum:** one section
  per slide, so `len(sections) == project.slide_count` when set (the value persisted by
  `POST /carousels` from `resolved_slide_count()`: POV default 9, Radar IA 7–8), else the deck size
  from `slides_config` via `slide_count_from_config()` (the helper the design payload already uses),
  else the content-mode default. Standalone generation uses the same content-mode default. Images
  generated = that many section images + 1 cover.
- **Entry points:** `POST /blog-posts/from-carousel` and `POST /blog-posts/generate` (202, async);
  always `status=draft`. The run is scheduled with the repo's existing tracked fire-and-forget
  pattern (`asyncio.create_task` + `_background_tasks` set + cancel-on-shutdown, like
  `editorial_workflow_resume_runner.schedule_background_resume`), **not** FastAPI `BackgroundTasks`
  or Celery. A periodic reaper in `run_workflow_workers` recovers runs killed by a restart.
- **Model routing** (ADR-0014): drafting/PT-EN copy = `LLM_MODEL_FAST`; quality judgement =
  `LLM_MODEL_REASONING`; persona score = fast; fallback on error/timeout/empty/bad JSON.

## Non-Goals

- The editor UI controls (AE-0424 wires them; D owns bulk generation + shared routes).
- Owner photo upload.
- Publishing automatically from a carousel (decision 1: always a draft).
- Multi-step review (F-14).

## Acceptance Criteria

- [x] AC1: `POST /blog-posts/from-carousel` creates a **draft** with `generation.status=in_progress`
      and returns 202; it 404s an unknown project and 409s when a **live blog row** already exists.
      "Live row" means **any non-deleted `blog_posts` row with that `project_id`**, regardless of
      status (`draft`, `under_review`, `approved`, scheduled, `published`, or hidden). The 409 body
      carries the existing post id; hidden bad posts are rebuilt by AE-0426, never by re-running
      from-carousel.
- [x] AC2: `POST /blog-posts/generate` creates a draft from a topic (+ optional persona/sources) and
      returns 202.
- [x] AC3: The generated article is one continuous body (not per-slide concatenation) whose sections
      have distinct narrative roles; no section restates the same source sentence verbatim.
- [x] AC4: The body's `voice_score` is `>= 70` or the writer performed exactly one rewrite pass; the
      score and breakdown are stored in `content.quality`.
- [x] AC5: A seeded repeated sentence and a seeded banned stock phrase are detected and reported.
- [x] AC6: The writer emits **exactly N sections** (N = carousel slide count: `project.slide_count`,
      else `slide_count_from_config()`, else the content-mode default; standalone uses the default).
      A mismatch is normalized (split/merge) or fails the generation with a clear error; it is never
      silently stored. The post gets **N+1 image slots** (cover + one per section); stored images are
      `<= N+1` because a failed slot stays `image=null`. Every image prompt contains no text, and a
      stored `image.alt` is non-empty.
- [x] AC7: A failed image leaves that slot `image=null`, records an error with the section id, and
      the draft is still usable with `generation.status=partial`.
- [x] AC8: An LLM failure leaves the draft row with `generation.status=failed` and no data loss;
      the owner can retry.
- [x] AC9: All LLM/image calls are Langfuse-traced with `content_type="blog_post"`, `project_id`,
      `phase`, `agent_name`, `user_id`; image count and voice score are logged.
- [x] AC10: The writer never emits an English research intro into the PT sections (F-05 class). The
      test is deterministic: a unique English sentence is seeded in the findings and asserted absent
      from every PT `body_md`; the same fixture is asserted present in `translations.en` (so the
      assertion cannot pass vacuously).
- [x] AC11: EN is gated like PT: the same voice/repetition checks run on
      `translations.en.sections` and its score is stored under `translations.en.quality`; an EN score
      below the threshold triggers the same single rewrite pass.
- [x] AC12: If the source carousel is private (`is_public = false`), the editor warns that the
      published post will 404 on the public site (ADR-0013 visibility gate: carousel-origin posts
      require the parent carousel to be public); the owner can make the carousel public or keep the
      post as a draft. The warning is covered by a test.
- [x] AC13: The route persists the draft and schedules the pipeline in a tracked in-process task;
      the row carries `generation = {status, started_at, heartbeat_at, lease_id, attempt, errors}`
      and heartbeats during the run. Every write is lease-fenced (`WHERE lease_id = :mine`), so a
      duplicate/retried task cannot clobber a newer run. `BLOG_GENERATION_TIMEOUT_SECONDS` (default
      900) bounds the run; `CancelledError` marks the row recoverable-failed and re-raises. No
      FastAPI `BackgroundTasks`, Celery/ARQ, or new queue.
- [x] AC14: A deploy/restart that kills the task leaves the row `in_progress`; the existing
      `run_workflow_workers` tick (default every 60 s) reaps rows whose
      `heartbeat_at < now - BLOG_GENERATION_STALE_SECONDS` (default 180) to `failed` with
      `ERR_GENERATION_INTERRUPTED`, `recoverable=true`, preserving partial content. The owner retries
      (same route/row); there is no automatic re-enqueue (avoids duplicate LLM/image spend). The
      reaper is safe under the single-replica assumption and the DB lease keeps it safe if that
      changes.

## Gherkin Scenarios

- `backend/tests/features/blog_generate_ae0425.feature` (writer, gate, images, failure, tracing).
- Scenario list: from-carousel always draft; 409 for any non-deleted row (including hidden);
  standalone generation; continuous body; voice gate rewrite; repetition detected; cover +
  per-section images; **exactly N sections + N+1 image slots (stored <= N+1)**; writer count
  mismatch handled; image failure partial; LLM failure; prompt-injection in a writing sample
  ignored; seeded English sentence absent from PT and present in EN; EN voice gate; private-carousel
  publish warning; restart mid-generation is reaped to failed/recoverable and a retry completes
  without a duplicate row; a timed-out run is failed; a duplicate schedule cannot clobber a newer
  lease.

## Delta

### ADDED

- `backend/src/rag_backend/agents/blog_writer/` (facade), `agents/prompts/blog/v1/*.md|yaml`.
- `application/services/blog/blog_generation_service.py`,
  `application/services/blog/blog_image_service.py`, `domain/constants/blog_voice.py`.
- Routes `backend/src/rag_backend/api/routes/blog_generate.py` (generation entry points only; the
  image routes are owned by AE-0424 and reused here — no new image routes).
- Settings: `BLOG_IMAGE_CONCURRENCY`, `BLOG_IMAGE_COST_CAP` (**no `BLOG_IMAGE_MAX`** — the count
  comes from the carousel `slide_count`), `BLOG_GENERATION_TIMEOUT_SECONDS` (900),
  `BLOG_GENERATION_STALE_SECONDS` (180).
- The blog-generation reaper in `application/workers/workflow_workers.py`.
- Feature spec above.

### MODIFIED

- Container wiring (writer agent, image service), `BlogPostResponse` (generation metadata), i18n
  copy ("Generate a carousel…" → generate-a-blog entry).

### REMOVED

- `build_blog_markdown_from_long_form_notes` for the blog body: the flat-markdown (v1) composition
  is dropped, not kept as a fallback. The writer consumes research/outline/notes as raw material and
  emits v2 sections directly.

## Affected Areas

- Backend: agents, application services, routes, settings, constants
- Frontend: entry-point buttons (from a carousel; standalone) in the dashboard
- Database: `content` (v2) + `ai_generation_metadata.generation` (no schema change)
- API: two new POST routes (202)
- Tests: backend feature + unit (writer, gate, images)
- Docs: ADR-0025, architecture companion, prompt README
- Prompts/LLM: new `blog/v1` prompts + image prompt template
- Observability: Langfuse phases `blog_generation`, `blog_section_image`; reaper logs/metrics for
  interrupted runs
- Deployment: normal; new env defaults must be documented

## Dependencies

- Blocks: AE-0426.
- Blocked by: AE-0423 (document shape). Related: AE-0424 (shares image routes).
- Related: ADR-0003, ADR-0014, ADR-0016, AE-0347, AE-0416.

## Implementation Plan

1. Feature spec + prompt files.
2. Writer agent + generation service + quality gate + unit tests.
3. Image service (bounded concurrency, cost cap, failure policy) + tests.
4. Routes + DI wiring + feature tests, including the tracked task, lease/heartbeat, timeout and
   restart reaper.
5. Frontend entry points.
6. Gates: `bash scripts/ci/gates.sh backend` and `frontend`.

## QA Checklist

- [ ] Security reviewed (prompt injection, image prompt sanitizer, rate limits, cost cap)
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested (empty research, missing persona, all images fail, cost cap hit)
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-10-18 16:30

Ticket created from the AE-0422 plan (ADR-0025, wave D).

### 2026-10-19 (worker)

- Backend: writer façade `agents/blog_writer/` (draft/rewrite on the fast model, judgement on the
  reasoning model, persona voice scorer, text-free image prompts) + prompts `agents/prompts/blog/v1/`;
  application `blog_quality_scan` / `blog_quality_gate` / `blog_section_plan` / `blog_brief` /
  `blog_generated_document` / `blog_image_service` / `blog_generation_service` /
  `blog_generation_runner`; lease-fenced SQL store + reaper; routes `from-carousel`, `generate`,
  `generation/retry`, `blog-images`; settings + `.env.example`; worker-tick reaper; shutdown cancel.
- Frontend: "Generate with AI" (blog dashboard), "Create blog post from this carousel" (carousel
  publish page), editor generation banner (progress / partial / failed + retry / interrupted /
  private-carousel warning with a link to the carousel visibility control), i18n PT/EN.
- Rebased onto the moved `origin/feat/ae-0423-blog-document-model` (17 new AE-0423 commits), clean.

## Files Touched

- Backend (new): `domain/constants/{blog_voice,blog_generation}.py`,
  `domain/models/{blog_generation,blog_generation_state}.py`, `domain/protocols/blog_generation.py`,
  `agents/blog_writer/{__init__,agent,constants,image_prompts,parsing,persona_block,voice}.py`,
  `agents/prompts/blog/v1/{system.md,draft.yaml,rewrite.yaml,judge.yaml,image_prompt.yaml,README.md}`,
  `application/services/blog/{blog_brief,blog_generated_document,blog_generation_runner,blog_generation_service,blog_image_service,blog_quality_gate,blog_quality_scan,blog_section_plan}.py`,
  `infrastructure/database/{blog_generation_drafts,blog_generation_store}.py`,
  `bootstrap/blog_generation.py`, `api/routes/{blog_generate,blog_generate_support,blog_images}.py`,
  `api/schemas/blog_generate.py`.
- Backend (modified): `application/services/blog_workflow_observability.py` (`blog_phase_trace`),
  `application/workers/workflow_workers.py` (reaper step), `bootstrap/app_factory.py` (routers,
  reaper, shutdown cancel), `api/routes/__init__.py`, `infrastructure/config/settings.py`,
  `backend/.env.example`, `tests/snapshots/openapi_routes.json`.
- Frontend (new): `modules/publishing/blog/generation/*` (requests, state, hooks, banner,
  from-carousel section, types), `app/dashboard/blog-posts/{generate-blog-post-modal.tsx,use-generate-blog-post.ts}`.
- Frontend (modified): `constants/api.ts`, `modules/publishing/index.ts`, blog-posts page, editor page,
  carousel publish page, `i18n/locales/{en,pt}.json`.
- Docs: ADR-0025 API table (retry + image routes), architecture companion §3.1 "As built".

## Test Evidence

Final run after the re-review fixes + rebase onto #147's reservation contract (each gate run individually, sequentially; live Postgres `DATABASE_URL`). Mutation lanes are NOT run locally (orchestrator rule after the 2026-10-19 OOM): CI's mutation gate is the source of truth.
Backend (all non-mutation gates):
GATES_JSON: {"pass":21,"fail":0,"skip":0,"results":[{"gate":"backend:format","status":"PASS"},{"gate":"backend:lint","status":"PASS"},{"gate":"backend:lint-diff","status":"PASS"},{"gate":"backend:blanket-ignore","status":"PASS"},{"gate":"backend:strict-diff","status":"PASS"},{"gate":"backend:type","status":"PASS"},{"gate":"backend:imports","status":"PASS"},{"gate":"backend:arch-ratchet","status":"PASS"},{"gate":"backend:docstrings","status":"PASS"},{"gate":"backend:dead-code","status":"PASS"},{"gate":"backend:inline-prompts","status":"PASS"},{"gate":"backend:redis-factory","status":"PASS"},{"gate":"backend:autopilot-env","status":"PASS"},{"gate":"backend:healthcheck-loopback","status":"PASS"},{"gate":"backend:bandit","status":"PASS"},{"gate":"backend:pip-audit","status":"PASS"},{"gate":"backend:integrity","status":"PASS"},{"gate":"backend:test","status":"PASS"},{"gate":"backend:diff-cover","status":"PASS"},{"gate":"backend:migrations","status":"PASS"},{"gate":"backend:schema-drift","status":"PASS"}]}
Frontend (all non-mutation gates, base `feat/ae-0424-section-editor`):
GATES_JSON: {"pass":16,"fail":0,"skip":0,"results":[{"gate":"frontend:lint","status":"PASS"},{"gate":"frontend:lint-changed","status":"PASS"},{"gate":"frontend:component-types","status":"PASS"},{"gate":"frontend:duplication","status":"PASS"},{"gate":"frontend:dead-code","status":"PASS"},{"gate":"frontend:typecheck","status":"PASS"},{"gate":"frontend:build","status":"PASS"},{"gate":"frontend:legacy-guard","status":"PASS"},{"gate":"frontend:legacy-inventory","status":"PASS"},{"gate":"frontend:format","status":"PASS"},{"gate":"frontend:security","status":"PASS"},{"gate":"frontend:integrity","status":"PASS"},{"gate":"frontend:test","status":"PASS"},{"gate":"frontend:schema-drift","status":"PASS"},{"gate":"frontend:duplication-tests","status":"PASS"},{"gate":"frontend:dead-files","status":"PASS"}]}


## QA Report

Pending.

## Decision Log

### PR #146 review fixes (2026-10-19)

1. **Heartbeat never replaces the run result.** Any `store.heartbeat` error other than a lost
   lease is logged (`blog_generation_heartbeat_failed`) and the loop keeps beating; the beat task
   is awaited with `asyncio.wait`, which never re-raises its outcome. Test: a `ConnectionError`
   heartbeat blip → the run still finishes `complete` and `finish()` runs.
2. **Owner edits during the image step survive — on AE-0424's shared slot-write path.** Every
   CONTENT write of the run (the article, then the images) goes through `apply_slot_edit`
   (`bootstrap/blog_generation_store.py`): the row is re-read `SELECT ... FOR UPDATE` after the
   provider spend, the edit is applied onto the LATEST document by section id (only EMPTY slots are
   filled, an owner-set image is kept, a section the owner deleted is skipped), stored with a
   version snapshot at the locked `lock_version` (an owner save is the base, never a 409), the
   lease is checked on the locked row, and the new image files are deleted when the write fails.
   The article write refuses to overwrite an article the owner already wrote
   (`generation_conflict`). Run state (heartbeat, final status) stays lease-fenced in
   `SqlBlogGenerationStore`. The editor is read-only (fieldset + save disabled) while
   `generation.status == in_progress` and adopts each newer server version while generating.
3. **Retry never regenerates an existing article.** `partial` is retryable too; when the stored
   document has a non-empty section the retry is `images_only` (no writer/gate) and fills only the
   missing slots. Images count on AE-0424's per-post cap (`blog_image_generations`,
   `BLOG_IMAGE_COST_CAP`, default 30 images, shared with the editor); the run only attempts what is
   left. A row whose content does not parse counts as "no article" (strict `parse_blog_content`,
   no read fail-safe — AE-0428 removes it): the retry reruns the writer instead of a 500.
4. **Single image store/route/template = AE-0424's** (see "One image path" below).
### PR #146 re-review fixes (2026-10-19)

- **A. Editor lock across a Retry.** The editor adopts a newer server version whenever EITHER its
  own copy or the server's (polled) copy is generating, so a Retry clicked in the editor locks the
  fields at once (server flipped to `in_progress`) and the images appear when the run completes,
  without a reload. Test: hook failed → retry → locked → unlocked with the cover image.
- **B. Unparseable rows.** The article write is a full-document replacement when the locked row
  does not parse as `blog.v2` (same versioned write: snapshot of the old content), so a retry of a
  legacy row ends `complete` instead of a paid 422 dead end. Tests: store (replace vs slot path),
  API (unparseable row → retry → final status `complete`, v2 with 7 sections + cover).
- **Budget reserved before the spend (AE-0424 review round 2 contract).** The run reserves its
  image slots one by one through `reserve_image_budget` (row lock + commit) BEFORE any provider
  call and only generates what was granted; the reservation is kept when a slot fails (it may be
  billed). Content writes no longer count images.
- **C. Orphans.** After the image write, the files of images whose slot vanished meanwhile (section
  deleted / filled by the owner) are deleted; they still count against the cap (they were paid).

- **Low: English in PT.** Besides stripping verbatim research sentences, a cheap per-section check
  (English vs Portuguese function words) reports PT sections that read as English; the finding
  goes to the judge and triggers the single rewrite.

### Implementation decisions (worker, 2026-10-19)

- **Retry route.** AC1 409s `from-carousel` for ANY existing row, so "retry on the same route/row"
  (AC14) cannot go through it. Added `POST /blog-posts/{id}/generation/retry` (202): only a `failed`
  run, same row, new lease + attempt, `lock_version` bumped (fences the old task); 409 while
  `in_progress` or after `complete`/`partial`. ADR-0025 API table updated.
- **One image path (orchestrator decision, PR review 2026-10-19).** AE-0424 (#147) owns the
  blog-images store (`BlogImageStore`), the single-image `BlogImageService`, the image template
  (`agents/prompts/blog/v1/image_prompt.yaml`, `{scene}`) and `GET /api/blog-images/{post_id}/{file}`
  (public; uuid4 names). AE-0425 rebased onto `feat/ae-0424-section-editor`, dropped its own
  route/template/service and builds bulk generation on top (`blog_image_batch.py`: concurrency,
  budget, best-effort slots). The PR now targets `feat/ae-0424-section-editor`.
- **Lease fence.** Run-state writes are `WHERE id AND generation.lease_id = :mine AND lock_version
  = :seen`; content writes check the lease on the `FOR UPDATE`-locked row inside AE-0424's slot
  write. A retry and the reaper rotate the lease and bump `lock_version`, so a stale task's writes
  fail (its new image files are deleted). Proven on SQLite and Postgres (the store tests run on
  both when `DATABASE_URL` is set).
- **Quality judgement on the reasoning model.** The gate's only model judgement is the revision
  notes for the single rewrite (`judge`, best-effort); drafting/rewrite/persona scoring stay fast.
  Rewrite is whole-article, once, re-normalized and re-scored; the second score is stored as is.
- **Source leak guard (AC10).** PT sentences copied verbatim from the (English) research findings are
  stripped deterministically before scoring; EN is untouched (the seeded oracle stays in EN).
- **Verbatim note copies** are reported as `repetition.repeated_sentences` (the `blog.v2` quality
  model has no separate field) and trigger the rewrite (AC3).
- **Count normalization (AC6).** Extra sections merge into the last; missing sections split the
  longest section on paragraph breaks; otherwise `section_count_mismatch` (run fails, nothing
  stored). N = `project.slide_count` → `slide_count_from_config(slides_config)` → content-mode
  default (POV family 9, Radar IA 7); standalone uses the default.
- **Image cap = AE-0424's.** `BLOG_IMAGE_COST_CAP` counts images per post (default 30; editor +
  every generation attempt); capped slots stay `null` with `image_cost_cap_reached`. (The earlier
  USD cap and its setting were removed: one cap, one setting.)
- **Generated body sanitization.** `sanitize_model_copy` + HTML-tag strip, not
  `sanitize_display_input` (that strips `( )` and would break markdown links); raw HTML is never
  rendered (react-markdown allow-list).
- **EN images** reuse the PT image file with their own alt text; `translations.en.quality` is stored.
- **Disclosure.** Generated rows carry `ai_disclosure_label = ai_generated` (QUAL-002).
- **`build_blog_markdown_from_long_form_notes` kept** (not deleted): the blog body no longer uses it
  (from-carousel runs the writer), but it still fills `carousel_projects.blog_markdown` for the
  distribution pack (LinkedIn input), which AE-0428 classifies as live.
- **Per-slot image controls** live in AE-0424's section editor (generate/regenerate per slot);
  the AE-0425 banner reports `N of M images` for a partial run and offers "Generate the missing
  images" (the images-only retry).
- **Not in mutmut's path list.** The new modules are not added to `[tool.mutmut] paths_to_mutate`
  (curated list); unit tests assert behavior (exact counts, findings, fences).

- **One writer, not per-slide.** Concatenating notes is the root cause of F-02/F-03; a single
  article pass with the persona style guide fixes both.
- **Voice gate is the quality control, not a premium model** (ADR-0014): drafting may use the fast
  tier as long as `evaluate_match >= 70` gates it.
- **Images are best-effort.** A failed image must never cost the owner their draft.
- **Image count follows the carousel (owner revision).** One section per slide means
  `len(sections) == project.slide_count` (validated by the writer); a separate `BLOG_IMAGE_MAX` would
  drift from the carousel
  and is removed. `BLOG_IMAGE_COST_CAP` is the only spend guard.
- **Always a draft.** Owner decision 1; no branch publishes.
- **In-process tracked task + reaper, not a new queue.** The backend already runs long work this way
  (`run_workflow_workers`, `editorial_workflow_resume_runner`); adding Celery/ARQ for one job would
  add a broker and a second deployment surface. The trade-off is that a restart kills the task, so
  the DB lease + heartbeat + periodic reaper are mandatory, and recovery is an owner retry rather
  than an automatic re-enqueue (duplicate generation costs money).

## Risk & Size

- **Risk:** High — LLM quality and image spend; mitigated by the voice gate, bounded concurrency, per-post cost cap and best-effort images.
- **Size:** L

## Blockers

None.

## Final Summary

Pending.
