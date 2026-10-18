# AE-0425 — Blog writer (voice) + GPT images + generation entry points (D)

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

- [ ] AC1: `POST /blog-posts/from-carousel` creates a **draft** with `generation.status=in_progress`
      and returns 202; it 404s an unknown project and 409s when a **live blog row** already exists.
      "Live row" means **any non-deleted `blog_posts` row with that `project_id`**, regardless of
      status (`draft`, `under_review`, `approved`, scheduled, `published`, or hidden). The 409 body
      carries the existing post id; hidden bad posts are rebuilt by AE-0426, never by re-running
      from-carousel.
- [ ] AC2: `POST /blog-posts/generate` creates a draft from a topic (+ optional persona/sources) and
      returns 202.
- [ ] AC3: The generated article is one continuous body (not per-slide concatenation) whose sections
      have distinct narrative roles; no section restates the same source sentence verbatim.
- [ ] AC4: The body's `voice_score` is `>= 70` or the writer performed exactly one rewrite pass; the
      score and breakdown are stored in `content.quality`.
- [ ] AC5: A seeded repeated sentence and a seeded banned stock phrase are detected and reported.
- [ ] AC6: The writer emits **exactly N sections** (N = carousel slide count: `project.slide_count`,
      else `slide_count_from_config()`, else the content-mode default; standalone uses the default).
      A mismatch is normalized (split/merge) or fails the generation with a clear error; it is never
      silently stored. The post gets **N+1 image slots** (cover + one per section); stored images are
      `<= N+1` because a failed slot stays `image=null`. Every image prompt contains no text, and a
      stored `image.alt` is non-empty.
- [ ] AC7: A failed image leaves that slot `image=null`, records an error with the section id, and
      the draft is still usable with `generation.status=partial`.
- [ ] AC8: An LLM failure leaves the draft row with `generation.status=failed` and no data loss;
      the owner can retry.
- [ ] AC9: All LLM/image calls are Langfuse-traced with `content_type="blog_post"`, `project_id`,
      `phase`, `agent_name`, `user_id`; image count and voice score are logged.
- [ ] AC10: The writer never emits an English research intro into the PT sections (F-05 class). The
      test is deterministic: a unique English sentence is seeded in the findings and asserted absent
      from every PT `body_md`; the same fixture is asserted present in `translations.en` (so the
      assertion cannot pass vacuously).
- [ ] AC11: EN is gated like PT: the same voice/repetition checks run on
      `translations.en.sections` and its score is stored under `translations.en.quality`; an EN score
      below the threshold triggers the same single rewrite pass.
- [ ] AC12: If the source carousel is private (`is_public = false`), the editor warns that the
      published post will 404 on the public site (ADR-0013 visibility gate: carousel-origin posts
      require the parent carousel to be public); the owner can make the carousel public or keep the
      post as a draft. The warning is covered by a test.
- [ ] AC13: The route persists the draft and schedules the pipeline in a tracked in-process task;
      the row carries `generation = {status, started_at, heartbeat_at, lease_id, attempt, errors}`
      and heartbeats during the run. Every write is lease-fenced (`WHERE lease_id = :mine`), so a
      duplicate/retried task cannot clobber a newer run. `BLOG_GENERATION_TIMEOUT_SECONDS` (default
      900) bounds the run; `CancelledError` marks the row recoverable-failed and re-raises. No
      FastAPI `BackgroundTasks`, Celery/ARQ, or new queue.
- [ ] AC14: A deploy/restart that kills the task leaves the row `in_progress`; the existing
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

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Decision Log

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
