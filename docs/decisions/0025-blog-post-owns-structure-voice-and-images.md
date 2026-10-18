---
status: proposed
date: 2026-10-18
decision-makers: Pedro Marins
consulted: QA report 2026-10-18 (F-01..F-15), Claude (planner/architect, branch docs/ae-0422-blog-architecture)
informed: delivery team
---

# ADR-0025: Blog post owns its structure, voice and images

## Context and Problem Statement

The blog is the most important surface of the site. Today a carousel-origin blog post is **not a
document**: it is a read-time *view over carousel data*, so it inherits the carousel's shape
(slides), its text (`long_form_notes`) and its images (rendered Instagram cards) and none of the
owner's voice. The 2026-10-18 production QA (REPORT.md) confirmed:

- **F-01 (blocker, images):** in-body "section images" are the **rendered carousel slides** — the
  Instagram cards with vertices/heading/body text baked in — not clean editorial art.
  `GET /api/carousels/{id}/design` returns `images.slides` byte-identical to
  `images.rendered_slides_pt`, because `design_token_utils.py:216-221` forces
  `merged_images["slides"] = default_list` (the rendered list from `:280,308-313`). The public page
  injects them between `##` sections (`blog-post-content.tsx:175-238`); the article hero is the only
  raw-art image (`/api/carousels/{id}/images/slide_1.jpg`).
- **F-02 (blocker, voice):** the body is a mechanical join of per-slide `long_form_notes`
  (`blog_composition.py:117-139`) and the persona is applied **only** to slide `draft_text`
  (`content_draft_agent.py:222-226`); `long_form_notes` pass through untouched (`:279-283`). The
  result is generic third-person AI prose, not the owner's first-person voice (ADR-0003
  contradicted for the blog).
- **F-03 (major):** heavy cross-section repetition and formulaic openers (one source sentence
  restated in every section); an essay-by-numbers.
- **F-05 (major, current):** older/current PT rows open with **English** research paragraphs
  (`BlogCompositionInput` comment, `blog_composition.py:49-60`). AE-0416 removed the research intro
  from *new* PT builds, but stored v1 rows still ship mixed; F-05 is stale only for rows rebuilt
  after 2026-10-17.
- **F-06 / F-15 (major/minor, editor):** the body is one raw-markdown `<textarea>`
  (`blog-post-edit-fields.tsx:100-115`); no per-section editing, no image add/remove/replace, no
  cover control, and `ImageGenModal` / `SeoPreview` / `AccessibilityChecker` are unwired.
- **F-07 (minor, a11y):** in-body `<img alt="">` (`blog-post-content.tsx:186`); `blog_image_map` is
  `null` everywhere, so images map **positionally** to H2 sections (`:228-236`) — wrong-section
  risk.
- **F-08 (minor):** stored markdown starts with `# <title>`, the page renders another H1 and strips
  the markdown one at read time (`stripLeadingH1`, `:240-252`); the editor shows the raw duplicate.
- **F-09 (major, generation):** no standalone AI blog generation and no "create blog from carousel"
  affordance; only running a whole carousel produces a blog (`use-new-blog-post.ts` posts an empty
  body; `POST /blog-posts` only slugifies).
- **F-10 (major, contract):** `ai-suggest` returns a fenced ```json envelope as the user-facing
  suggestion (`blog_post_ai_service.py:93-99` parses `json.loads` once, no fence handling).
- **F-11 (major, voice):** the AI panel is rendered without a `personaId`
  (`edit/page.tsx:140-144`), so persona scoring/enforce is unreachable from the editor.
- **F-12 / F-13 (major, editor):** no unsaved-changes guard; `version_history` is appended **only**
  in the restore handler (`blog_post_versions.py:88`), never on save — history is always empty and
  rollback 404s.
- **F-14 (major, editor):** no publish control for standalone posts (`submitForReview`/`approve`/
  `publish` exist in `use-blog-posts.ts:146-170` but no component calls them).

Owner decisions (binding, 2026-10-18; revised by the owner 2026-10-18 after review): carousel-origin
posts are **always drafts** (a carousel going public never publishes its blog post); images are
**all** generated with the OpenAI GPT image model (`gpt-image-2`; the same provider
`POST /blog-posts/{id}/generate-image` already resolves via
`image_provider_registry().resolve(IMAGE_MODEL_OPENAI, IMAGE_STYLE_CINEMATIC)`,
`blog_post_ai.py:90-98`), **no carousel slide images** in blog posts, **no text in generated
images**, owner photo upload is **out of scope**; the bad already-published posts get hidden now and
rebuilt later as drafts. Revised decisions: the **multi-step review workflow and scheduled publish
are IN scope** (draft → under review → approved → published, or publish at a future
`scheduled_publish_at`); the **number of generated section images follows the same `slide_count`
used when the carousel was created** (`CarouselProject.slide_count` / `resolved_slide_count()`),
never a separate blog-only maximum; **PT/EN language buttons switch the whole document** (editor and
public page), not just UI chrome; and the **legacy `blog_image_map` plus the dead blog-v1 files are
dropped** (AE-0428), not kept behind a flag.

Root cause: **a blog post is a view over carousel data, not its own document.** This ADR makes the
post a document that owns its structure, its voice and its images, while keeping the carousel as an
input to generation and keeping the existing public/private API split (ADR-0013) and JSONB store
(ADR-0006).

## Decision Drivers

- The post must read like the owner wrote it (persona voice, first-person, no boilerplate).
- The post must carry its own editorial images (generated), never Instagram-card screenshots.
- The owner must edit each section, including add/remove/replace/reorder its image and the cover.
- No data loss and a reversible, idempotent data cutover (JSONB rewrite, no DDL).
- One canonical store (ADR-0006/0009/0011); no second representation and no dual source of truth.
- Preserve the public/private trust boundary and lean payload (ADR-0013).
- Keep the carousel pipeline frozen (ADR-0007/0021: "v2 stays v2"); the blog writer is additive.
- Single author, single tenant, pre-production operating context (ADR-0009 §1).

## Considered Options

1. **Keep the carousel-view and patch it** — keep composing markdown from `long_form_notes`,
   keep injecting carousel images at read time, only fix the forced `slides` override and add a
   persona pass on the notes.
2. **Flat markdown + a `blog_image_map`** — keep the single markdown body and store a
   section-heading → image mapping the owner can edit.
3. **Structured sections in `blog_posts.content` JSONB (chosen)** — a versioned document with a
   cover and an ordered list of sections, each with its own markdown body and optional image;
   written by a new blog-writer step; rendered directly by the public page.
4. **A separate `blog_post_sections` table** — normalize sections to rows.

### Option comparison

| Option | Structure | Per-section image/edit | Voice | Migration risk | Verdict |
|---|---|---|---|---|---|
| 1. View + patch | none (markdown) | no | patch at note level | none | Rejected — the post still cannot own images or per-section edits; the slide/text coupling that caused F-01/F-02 remains |
| 2. Flat markdown + image map | heading-keyed map | partial (fragile positional/heading keys) | possible | low | Rejected — reordering/renaming a section silently loses its image (the F-07 class of bug); no stable section identity |
| 3. Sections JSONB | cover + ordered sections | yes (stable ids) | yes (writer step) | low, reversible | **Accepted** |
| 4. Sections table | rows | yes | yes | high (migration + joins + a second writer vs the row) | Rejected — premature normalization for a 1:1, ordered payload the ACL already loads alongside the body (same reasoning as ADR-0011 Option 1) |

**Rejected sub-decision — keep a dual v1/v2 read path for a gradual rollout.** A versioned reader that
accepted both the old flat markdown and the new document would let the model ship without a cutover
and would keep old rows rendering. It is rejected: it drags the old shape (and its bugs) through the
public renderer and the editor indefinitely, doubles the parsing/validation surface, and is exactly
the "old slop" the owner asked to drop. The cutover is cheap (pre-production, single user,
ADR-0009 §1) and is done in one shot; after `--verify`, v2 is the only persisted shape (the
temporary read fail-safe is removed in AE-0428).

## Decision Outcome

Chosen: **Option 3 — the blog post owns a versioned structured document in `blog_posts.content`
(JSONB), with a generated cover and one generated image per section, written in the persona voice.**

### Data model (`blog_posts.content`, schema `blog.v2`)

```jsonc
{
  "schema": "blog.v2",
  "cover": {
    "url": "https://…/blog-images/<post>/<uuid>.jpg",
    "alt": "string (required, non-empty)",
    "caption": "string|null",
    "source": "generated",
    "prompt": "string",          // the sanitized prompt actually sent
    "model": "gpt-image-2",
    "created_at": "2026-10-18T12:00:00Z"
  },
  "sections": [
    {
      "id": "sec_<uuid4>",       // stable identity (reorder/rename safe)
      "heading": "string|null",  // null allowed for the lede
      "body_md": "string",       // sanitized markdown, no leading H1
      "image": null              // or the Image object above
    }
  ],
  "translations": {
    "en": { "schema": "blog.v2", "cover": null, "sections": [ /* same shape */ ],
            "quality": { /* same shape, null until scored */ } }
  },
  "quality": {
    "voice_score": 82.0,
    "voice_breakdown": { "tone_match": 84.0, "overall": 82.0, "suggestions": [] },
    "repetition": { "repeated_sentences": [], "banned_phrases": [] },
    "rewrite_passes": 1,
    "checked_at": "2026-10-18T12:00:00Z"
  }   // or null when not scored (in-progress / migrated)
}
```

Rules and justifications:

- **Bootstrap shape during generation.** A `from-carousel`/`generate` row starts as
  `{"schema":"blog.v2","cover":null,"sections":[],"translations":{},"quality":null}`. `sections` may
  be empty **only** while `ai_generation_metadata.generation.status == "in_progress"`; `publish`
  requires >= 1 non-empty section. `quality` is nullable in general: `null` means "never scored"
  (in-progress or a row migrated from v1); the voice gate still runs before generated content is
  stored.
- **Canonical document.** PT sections are canonical (`sections`). EN is a translation inside the
  same JSONB object, mirroring the current `blog_translations` intent; the writer produces both.
  `distribution` (`caption`, `linkedin_post_*`) stays where ADR-0011 put it — untouched.
- **`featured_image_url` stays and is kept in sync with `cover.url`** (write-through on save and on
  image generation; the cutover sets it to `NULL` when it sets `cover = null`, so the invariant
  holds from the first v2 row). A null cover is legal at publish: cards/OG fall back to a
  deterministic neutral title card / site default, never to a carousel slide. Justification: `featured_image_url` is a public allow-listed field (ADR-0013),
  is read by listing cards / OG images, and is a flat, indexed-friendly column. Removing it would
  force every list/card consumer to parse JSONB. The column is the *projection*, `content.cover` is
  the *source of truth*; exactly one writer path writes both, in one transaction.
- **Stable `id` per section.** Reordering and renaming never detach an image (fixes F-07 class).
- **`image.alt` is mandatory and non-empty**; the renderer never emits `alt=""` (fixes F-07).
- **No leading `# <title>` in any `body_md`.** The title is a top-level column; the renderer renders
  it once (fixes F-08). The writer is instructed never to emit an H1; the cutover strips one.
- **`model` / `prompt` are recorded** for cost attribution, reproducibility and the "regenerate with
  edited prompt" editor affordance, but they are **editor-only**: the public projection excludes
  them (see below).
- **EN is gated too.** The writer runs the same voice/repetition checks on
  `translations.en.sections`; its scores live under `translations.en.quality` (same shape as the PT
  `quality`). Publishing exposes only a gated translation; the editor shows the EN score next to the
  EN tab.
- **Owner upload is out of scope**: `source` is currently always `"generated"`; the enum leaves
  room for `"upload"` as a recorded follow-up without a schema change.

### Single shape: v1 is dropped, not supported

**There is exactly one content shape after B: `blog.v2`.** We deliberately do **not** keep a v1
(flat-markdown) read path, a `legacy_markdown` blob, or a dual-shape branch. "Refactor over keeping
old slop": the old shape is migrated once and then removed from the code, not carried forever.

- **Cutover (one-shot backend command; no Alembic dependency):** `python -m
  rag_backend.scripts.blog_v1_to_v2` (in the built backend image) rewrites every v1 row in place.
  It supports `--dry-run` (counts + sample rows, no writes), `--apply` (idempotent, batched, one
  transaction per batch, `pg_advisory_xact_lock`), `--verify` (exit non-zero if any row is still
  non-v2) and `--rollback` (re-join sections; only with a code rollback). For each row and for
  **every language in `content.translations`** (the real v1 shape is
  `{"markdown": "...", "translations": {"en": "..."}}` — `blog_translations` is `dict[str,str]`),
  split on `^## ` **outside fenced code blocks**, strip a leading `# <title>`, assign fresh
  `sec_<uuid4>` ids, store the body **raw** (no sanitization), and set `cover = null` /
  `image = null` / `quality = null` / `featured_image_url = null`; write
  `translations.en = {"schema":"blog.v2","cover":null,"sections":[...],"quality":null}`. Non-string
  translation entries are dropped, not stringified. Non-markdown content becomes one empty section
  (never `str(dict)`); oversized sections are flagged for the rebuild, not truncated. The original
  flat markdown is not retained. **No image is carried** — v1 images were injected at *read time*
  from carousel design and were never stored on the post. Properties:
  - **idempotent** — a row already at `schema == "blog.v2"` is skipped (a re-run is a no-op);
  - **reversible at the data level** — `--rollback` (run from the new image **before** reverting the
    app code) re-joins `## {heading}\n\n{body_md}` for PT and each translation; body bytes are
    preserved exactly, headings normalize to `## `, and the title H1 is not restored; meaningful only
    with a code rollback to the pre-B release;
  - **fence-safe** — a `## ` line inside a fenced block is not a section boundary.
- **Why not Alembic.** `deploy.yml:255-262` disables migrate-on-deploy: prod was never
  Alembic-stamped and the chain had two heads, so `alembic upgrade head` aborted and took prod down
  on 2026-06-18; prod still bootstraps with `create_all`. Making the head merge + `alembic stamp`
  reconcile (`docs/deployment/prod-migration-reconcile.md`, AE-0207) a prerequisite would couple a
  safe JSONB rewrite to an unrelated, risky schema reconcile. The one-shot command is independent,
  runnable by the operator, and needs no DDL. The Alembic reconcile stays a separate prerequisite for
  **schema** migrations, not for this cutover.
- **Ordering is guaranteed by the deploy.** `deploy.yml` builds the image, `down`s the stack (no
  old/new overlap), starts Postgres, runs the one-shot with `--apply --verify` against the freshly
  built backend image, and only then `up -d`s the app. A non-zero exit aborts the deploy before the
  app serves traffic. The same command is safe for the operator to re-run.
- **The parser is strict for writes, with a temporary read fail-safe.** `parse_blog_content(content)`
  accepts **only** v2 and raises on anything else; no write ever stores v1. If the cutover has not
  run (operator error, partial deploy), the public/editor read catches `InvalidBlogDocumentError`
  and, when the row still has legacy `markdown`, adapts it **in memory** to a read-only v2 document
  with the same fence-aware splitter (text only, `cover/sections.images = null`, `quality = null`).
  That keeps every published post served (never a 500), never reads carousel slides, and emits the
  `blog_v2_non_migrated_rows` metric. The adapter is removed in AE-0428 after `--verify` reports zero
  non-v2 rows; it is not a supported v1 write/persist path.
- **A (AE-0422) keeps rendering the legacy markdown, without slides, until B merges.** A ships before
  the model exists, so it still reads v1 markdown (text only, no carousel images). B replaces that
  handling with the v2 renderer + cutover in the same release.
- **Backfill of images is explicit, not part of the cutover.** Migrated rows start with
  `cover = null` and image-less sections; the owner (or the E-ticket rebuild) generates images with
  the new pipeline. This keeps the cutover instantaneous and side-effect-free.

### Public rendering

- Render `cover` (or a neutral default when `cover` is null) as the hero, then each section's
  `heading`, `body_md`, and its own `image` (with `image.alt`). **Stop reading carousel design for
  blog images.** `resolveSlideImage` and the positional `blog_image_map` read are deleted (fixes
  F-01/F-07); the field itself is dropped from the carousel payload in AE-0428. The renderer
  consumes v2 only.
- Carousel design tokens may still be fetched **only for theme** (colors/typography) on
  carousel-origin posts, exactly as ADR-0013's detail-page branch already does — but never for
  images.
- The renderer renders the title **once** and never strips an H1 (the stored body has none) —
  fixes F-08 as a consequence of the model, not a read-time patch.
- Markdown is rendered through the existing allow-list (`react-markdown` `allowedElements` +
  `isSafeMarkdownHref`, `blog-post-content.tsx`), never `dangerouslySetInnerHTML`.

### Generation pipeline

Two entry points, one writer:

- **From a carousel** (carousel-origin): `POST /blog-posts/from-carousel` (see API contract)
  composes the inputs from the frozen carousel artifact (research findings, outline, per-slide
  `long_form_notes`) and runs the writer. **Always creates a draft** (owner decision 1). A carousel
  going public never flips its blog row to published.
- **Standalone** (topic + persona): `POST /blog-posts/generate` produces a draft from a topic and an
  optional persona/research brief (fixes F-09).

Pipeline (sequence):

```mermaid
sequenceDiagram
    actor Owner
    participant API as Blog API
    participant W as BlogWriterAgent (voice)
    participant G as QualityGate
    participant IMG as GPT image (gpt-image-2)
    participant DB as blog_posts (draft)

    Owner->>API: POST /blog-posts/{from-carousel|generate}
    API->>DB: create draft (status=draft, generation=in_progress)
    API-->>Owner: 202 Accepted {id, generation.status=in_progress}
    API->>W: write ONE article (research+outline+notes, persona style guide+samples, PT/EN)
    W-->>API: {cover_prompt, sections[], translations.en}
    API->>G: PersonaAgent.evaluate_match(body) + deterministic repetition/AI-cliché scan
    alt voice_score < 70 or repetition findings
        G-->>W: one rewrite pass (section-scoped)
        W-->>API: revised sections
    end
    API->>DB: store sections + quality scores
    par bounded concurrency (IMAGE_CONCURRENCY, cost cap)
        API->>IMG: cover image (prompt from title+lede, editorial, no text)
        API->>IMG: one image per section (prompt from section text, editorial, no text)
    end
    IMG-->>API: url | failure
    API->>DB: attach images; failures leave image=null + generation.errors[]
    API->>DB: generation.status=complete (or partial) — post stays draft
    Owner->>API: GET /blog-posts/{id}  (editor polls)
```

- **Run model (202 = in-process tracked task, not a new queue).** The route persists the draft and
  schedules the pipeline with the repo's existing fire-and-forget pattern
  (`asyncio.create_task` + a module-level `_background_tasks` set, task name, cancel-on-shutdown),
  the same mechanism as `editorial_workflow_resume_runner.schedule_background_resume`
  (`editorial_workflow_resume_runner.py:74,105-115`). No FastAPI `BackgroundTasks`, no Celery/ARQ.
  The task records `generation = {status, started_at, heartbeat_at, lease_id, attempt, errors}` and
  heartbeats; each write checks the lease (`WHERE lease_id = :mine`) like the carousel run-epoch
  fence, so a duplicate worker cannot clobber the row. `BLOG_GENERATION_TIMEOUT_SECONDS` (default
  900) wraps the run with `asyncio.wait_for`; `CancelledError` marks the row recoverable-failed and
  re-raises. A deploy/restart kills in-process tasks, so the existing periodic
  `run_workflow_workers` tick (`workflow_workers.py:212-260`, every
  `workflow_worker_interval_seconds`, default 60) gains a **blog generation reaper** that runs
  alongside the carousel stale-run reaper: rows still `in_progress` with
  `heartbeat_at < now - BLOG_GENERATION_STALE_SECONDS` (default 180) become `failed` with
  `ERR_GENERATION_INTERRUPTED`, `recoverable=true`, partial content preserved. The owner retries;
  there is no automatic re-enqueue (avoids duplicate LLM/image spend). A single backend replica is
  assumed; the DB lease still makes the reaper safe if that changes.
- **One continuous article.** The writer is a single agent/service (not per-slide), prompted with
  the **persona style guide + `persona.writing_samples[:5]`** (`persona_agent.py:87-116`) and given
  research findings + outline + `long_form_notes` as *raw material*, not as text to concatenate. It
  returns sections with distinct narrative roles. This fixes F-02/F-03.
- **Placement (ADR-0009 / ADR-0016).** The orchestration façade is a new agent package
  `agents/blog_writer/` (`agent.py` + `prompts/` via the shared registry `agents/prompts/blog/v1/`),
  and the business logic is `application/services/blog/blog_generation_service.py`; the bounded
  context will be extracted as `modules/blog/` in a follow-up once the shape settles. Prompts live
  in `.md`/`.yaml` per the prompt standard — never in `.py`.
- **Model routing (ADR-0014, current `docs/backend/llm-model-routing.md`):** article drafting and
  PT/EN copy = **fast** (`LLM_MODEL_FAST`); quality/rubric judgement = **reasoning**; persona
  enforce/scoring = **fast**; fallback `LLM_MODEL_FALLBACK` on error/timeout/empty/bad JSON. The
  voice gate (below) is what protects quality, not a premium model.
- **Quality gate (blocking, deterministic + model):**
  1. `PersonaAgent.evaluate_match(body)` — `overall >= 70` (ADR-0003's bar, `persona_agent.py:47-81`;
     `_on_hundred_point_scale` handles 0–10 answers, AE-0398/0407). Below 70 → **one** rewrite pass
     (whole article, or the sections named by the breakdown), then re-score and store.
  2. Deterministic scan: repeated sentences across sections, and a **banned stock-phrase list kept
     as data** (`domain/constants/blog_voice.py`; e.g. "no mundo de hoje", "é importante ressaltar",
     "em resumo"). Findings are recorded; a section that still repeats a sentence is rewritten once.
  3. The same gate runs on `translations.en.sections`; its score is stored under
     `translations.en.quality`. PT scores live in `content.quality` and are mirrored to
     `ai_generation_metadata.voice_score` for the listing/editor badge.

### Image generation contract and cost/failure policy

- **Provider:** `image_provider_registry().resolve(IMAGE_MODEL_OPENAI, IMAGE_STYLE_CINEMATIC)` —
  `gpt-image-2` (`blog_post_ai.py:90-98`). One provider, one style. Provider URLs expire, so the
  bytes are downloaded and persisted to the blog-images store; only the canonical
  CDN/same-origin URL is written to the document.
- **Scope:** exactly a **cover + one image per section** (owner decision 2). No carousel slide
  images, rendered or raw.
- **Prompt:** derived deterministically from the section heading + body (or title + lede for the
  cover) through a versioned template under `agents/prompts/blog/v1/image_prompt.yaml`; passed
  through `sanitize_image_prompt` (`image_prompt_sanitizer.py`) as the fallback safety net; the
  template **must instruct "no text, no words, no letters, no numbers"** (owner decision 2). The
  editor lets the owner edit the prompt and regenerate.
- **Count (owner revision):** the section count is the **carousel's slide count**, not a blog-only
  cap. A carousel-origin post produces one section per slide, so `len(sections) ==
  project.slide_count` when set (the value persisted by `POST /carousels` from
  `resolved_slide_count()`: `POV_SLIDE_COUNT_DEFAULT` 9, Radar IA 7 or 8), else the deck size
  derived from `slides_config` via the same `slide_count_from_config()` helper the design payload
  uses (`design_token_utils.py`), else the content-mode default (`content_mode.py:51-55`). The
  document is validated to have exactly that many sections (a writer mismatch is normalized or
  fails; it is never silently stored) and **N+1 image slots** (cover + one per section). Stored
  images are `<= N+1` because a failed slot stays `null`. Standalone generation has no project and
  uses the content-mode default. There is **no `BLOG_IMAGE_MAX`** setting; `BLOG_IMAGE_COST_CAP`
  remains the safety ceiling.
- **Concurrency and cost:** bounded worker pool (`BLOG_IMAGE_CONCURRENCY`, default 2); cover first,
  then sections; the whole step is best-effort and aborts when `BLOG_IMAGE_COST_CAP` is hit.
- **Failure policy:** a failed image never blocks the draft — the section is stored with
  `image = null`, the failure is recorded in `ai_generation_metadata.generation.errors[]` with the
  section id, and the editor shows a **visible per-slot retry**. Only an *LLM* failure (no article)
  fails the generation, and even then the draft row exists with `generation.status = failed` so the
  owner can retry.

### Editor interaction model

- Replace the single textarea with **section cards**: each card edits `heading` + `body_md`, can be
  reordered, added and deleted. A **cover slot** and a **per-section image slot** each support
  generate (GPT) / regenerate with an edited prompt / remove / set alt + caption. `"Rewrite this
  section in my voice"` calls `PersonaAgent.enforce` on one section (fixes F-06/F-11/F-15).
- **Voice score display** from `content.quality` (badge + breakdown), so the owner sees the gate.
- **Version snapshot on every save** (fixes F-13): `OptimisticLockService.apply_versioned_update`
  appends a `version_history` entry (title + content snapshot) inside the same transaction as the
  PUT. Restore keeps working (existing endpoint); the chicken-and-egg is removed.
- **Unsaved-changes guard** (fixes F-12): a route/`beforeunload` guard while the draft differs.
- **AI-suggest strict JSON** (fixes F-10): the service strips fences and validates the envelope; a
  response that is itself a nested envelope is unwrapped, and a non-conforming response degrades to
  the raw text with a plain explanation — never a fenced blob in a user field.
- **PT/EN language buttons** (owner revision) switch the **whole document** being edited: PT edits
  `content.cover` + `content.sections`; EN edits `content.translations.en.cover` + `.sections` (same
  shape). Switching never mutates the other language, and saving persists only the active language
  (the client sends the merged document, so the inactive language is byte-identical). When
  `content.translations.en` is missing the EN tab offers **"Generate EN translation"**, which runs
  the writer on the PT document and stores the result; until then the EN tab is read-only and the
  public page falls back to PT. The same two buttons on the public post switch
  `/blog/{id}?lang=pt|en` (PT fallback when EN is absent) — this is *content* language, independent
  of the next-intl UI locale.
- **Approval is invalidated by edits.** Any content edit while `under_review`, `approved`, or
  scheduled resets `status = "draft"` and clears `scheduled_publish_at` (the reviewer must see what
  will be published); `DELETE …/schedule` cancels without touching content. The due-post sweep only
  publishes rows still `approved`, so an edit automatically removes a post from the schedule.
- **Review and scheduled publish** (owner revision) replace the earlier plain-Publish-only decision:
  keep the existing `submit-review` → `approve`/`reject` and `schedule` routes and give them editor
  controls. Draft → under review (reviewer required) → approved → publish now, or schedule a future
  `scheduled_publish_at` (lead time validated); `unpublish` still returns the row to `draft`
  (ADR-0013 invariant: non-published ⇒ uniform public 404). The single-author deployment may
  self-approve behind `BLOG_ALLOW_SELF_REVIEW` (default **false**; enable it explicitly in the
  single-author deployment): the setting bypasses only the
  submit-time `ERR_SELF_REVIEW` guard, and the author is stored as the assigned reviewer so
  `assert_blog_post_reviewer_or_admin` already passes for approve/reject. When false, a distinct
  reviewer is required. With self-review enabled, a **"Publish now"** action on a draft auto-submits
  and self-approves before publishing (one click, same states underneath); with it disabled, the UI
  requires the explicit review steps.
- **Optimistic locking stays** (AE-0296) and widens: **every route that mutates `content`**
  (PUT, image generate/regenerate/patch/delete, rewrite, restore-version) requires `If-Match`;
  review/schedule/publish/unpublish keep it. Background generation writes through the same
  `version_history`/lock path and re-reads the row before its final write, so an owner edit during
  `generation_in_progress` is not silently lost (the job fails with a conflict and the draft is
  preserved).

### API contract changes

All blog routes stay under the `EditorUser` auth dependency and the existing rate limits unless
noted. Shapes below are additive to `BlogPostResponse` / `BlogPostUpdate`.

| Method & path | Request | Success | Notes |
|---|---|---|---|
| `POST /blog-posts` | `BlogPostCreate` (content validated as v2 if a `schema` is present) | `201` draft | unchanged; still slug-only when content is empty |
| `POST /blog-posts/from-carousel` | `{project_id, persona_id?, language?}` | `202` `{id, generation:{status:"in_progress"}}` | always a **draft**; 404 if the project is unknown; 409 if the project already has a non-deleted blog row |
| `POST /blog-posts/generate` | `{topic, persona_id?, language?, source_urls?[]}` | `202` `{id, generation:{status:"in_progress"}}` | standalone generation (F-09) |
| `GET /blog-posts/{id}` | — | `200` `BlogPostResponse` incl. `content` v2 + `ai_generation_metadata.generation` | editor poll |
| `PUT /blog-posts/{id}` | `BlogPostUpdate` (`content` may be v2) + `If-Match` | `200` | 422 invalid section shape; 409 lock conflict; appends a version snapshot |
| `POST /blog-posts/{id}/cover/image` | `{prompt?}` + `If-Match` | `200` `{cover}` | generate/regenerate cover; 502 image failure; persists bytes to the blog-images store |
| `DELETE /blog-posts/{id}/cover/image` | — + `If-Match` | `200` | clears `cover`, syncs `featured_image_url` |
| `POST /blog-posts/{id}/sections/{section_id}/image` | `{prompt?}` + `If-Match` | `200` `{image}` | generate/regenerate a section image; persists bytes |
| `PATCH /blog-posts/{id}/sections/{section_id}/image` | `{alt?, caption?}` + `If-Match` | `200` | alt must be non-empty |
| `DELETE /blog-posts/{id}/sections/{section_id}/image` | — + `If-Match` | `200` | |
| `POST /blog-posts/{id}/sections/{section_id}/rewrite` | `{persona_id?}` + `If-Match` | `200` `{section}` | `PersonaAgent.enforce` on one section |
| `POST /blog-posts/{id}/submit-review` | `?reviewer_id=` | `200` | draft → `under_review`; existing; reviewer must differ unless `BLOG_ALLOW_SELF_REVIEW` |
| `POST /blog-posts/{id}/approve` / `/reject` | `/reject?reason=` | `200` | reviewed → `approved` / back to `draft`; existing |
| `POST /blog-posts/{id}/publish` / `/unpublish` | — (+`If-Match`) | `200` | approved → `published` / published → `draft`; editor buttons |
| `POST /blog-posts/{id}/schedule` | `{scheduled_publish_at}` + `If-Match` | `200` | approved + future timestamp → scheduled publish; existing sweep |
| `DELETE /blog-posts/{id}/schedule` | — + `If-Match` | `200` | cancels the schedule; post stays `approved` |
| `POST /blog-posts/{id}/ai-suggest` | `{text, suggestion_type, context?}` | `200` | response `suggested_text` is plain text, never a fenced JSON envelope |
| `GET /blog-posts/{id}/versions` / `POST …/restore-version/{n}` | — + `If-Match` on restore | `200` | now populated on save; restore is a content mutation |

Public read (`GET /api/public/blog-posts/{id}`, ADR-0013) keeps its lean allow-list, but `content`
is **projected**, not serialized as-is. The public allow-list is:
`schema`, `cover{url,alt,caption,source,created_at}`, `sections[{id,heading,body_md,image{...}}]`,
and the same for `translations.en`. **Excluded:** `quality` (voice/repetition scores),
`image.prompt`, `image.model`, and all generation metadata. A contract test asserts the excluded
keys never appear in the public payload.

### Cutover, backfill and rollback

- **Schema:** none (still JSONB `content`); only the **one-shot command** rewrites v1 rows to v2.
  No Alembic revision is added (the chain is disabled in prod); the column shape stays stable.
- **Backfill:** none automatic. Images are generated by the owner or by the E-ticket rebuild; every
  published carousel-origin row is hidden first (below).
- **Rollback:** `blog_v1_to_v2 --rollback` re-joins `## heading` + `body_md`, meaningful only with a
  code rollback to the pre-B release. There is no stored `legacy_markdown` blob and no v1 write path
  in the new code; roll forward is the primary path.
- **Hiding old-pipeline rows (owner decision 3, prod action by the orchestrator):** hide **every**
  `status == "published"` `origin == "carousel"` row (all 10 live posts were built by the old
  pipeline) — no body-length or H1-stub filter. Hidden = the existing **unpublish** transition
  (published → draft, publish stamps cleared, status event emitted; public uniform 404, ADR-0013)
  **plus** a durable marker `ai_generation_metadata.hidden_bad_post = {at, reason}`. No row is
  deleted. The E-ticket selects the marker (not `status`) and rebuilds them as drafts through the new
  pipeline.

### Security

- **XSS in markdown:** section `body_md` is sanitized at the **write boundaries** (save/rewrite, via
  `sanitize_display_input`, as `content_draft_agent.py:283` already does for notes) and rendered
  through the `react-markdown` allow-list + `isSafeMarkdownHref`; **no
  `dangerouslySetInnerHTML`**. The cutover deliberately stores raw bytes (no silent mutation) and
  relies on the render allow-list; raw HTML in markdown is not rendered.
- **Prompt injection in persona samples / inputs:** persona `writing_samples`, topic and research
  text are **untrusted content**. `PersonaAgent` already runs `sanitize_llm_input` on content and
  context (`persona_agent.py:36-37,49`) and the carousel path already sanitizes inputs; the new
  writer must pass every source through `sanitize_llm_input` and delimit sources as data, never as
  instructions. A `.feature` asserts an injected instruction in a writing sample does not change
  the output contract.
- **Image prompt injection / moderation:** the primary defense is the versioned image-prompt
  template (no brands/people/text); `sanitize_image_prompt` is the fallback net. No URL is fetched
  (no SSRF); the model only receives sanitized text.
- **AuthZ / rate limits:** every new route is `EditorUser` and rate-limited like the existing AI
  routes (`RATE_LIMIT_AI_ENDPOINTS`); image generation is additionally bounded by the per-post cost
  cap.
- **Uniform 404:** no new public surface; unpublish/hide flips to `draft` (ADR-0013).

### Observability (Langfuse)

Every LLM/image call is traced with the required metadata (`project_id`, `phase`, `agent_name`,
`user_id`, `content_type="blog_post"`). New phases: `blog_generation` (writer + rewrite) and
`blog_section_image` (one per image). Logs (structlog) emit `voice_score`, `rewrite_passes`,
`repetition_findings`, image `model`/`cost`/`failure_reason` and per-post image count, so cost and
quality are attributable per post.

### i18n (PT/EN)

PT is canonical; EN lives under `content.translations.en` in the same shape (cover + ordered
sections + per-section images). The writer produces both; a missing EN translation falls back to PT
at render time. **Language buttons switch the content, not just the UI:** in the editor the PT/EN
toggle changes which document subtree is shown and saved (the inactive language is preserved
verbatim), and on the public post the same buttons navigate to `/blog/{id}?lang=pt|en` (the page
already resolves the `lang` query parameter through `resolvePublicBlogView(id, lang)`). An EN
translation that is absent is read-only in the editor with a "Generate EN translation" action; the
public page never 404s for a missing translation, it serves PT. The IG caption and LinkedIn posts
stay in `distribution` (ADR-0011). No English research text may appear in the PT sections (the
writer is language-scoped, fixing the F-05 class for rebuilt rows).

### Cleanup: drop `blog_image_map` and the dead blog-v1 files

The v2 refactor deletes the v1 machinery instead of leaving it behind a flag (AE-0428). Concretely:

- **`blog_image_map` end-to-end:** remove the field from `CarouselProject`
  (`domain/models/carousel.py:146`), content synthesis (`nodes/content/core.py:146-159`), the design
  payload (`carousel_template/design.py:77`), the carousel schemas (`api/schemas/carousel.py:247`,
  `media.py:262`, `preview.py:218`), the frontend schema (`schemas/carousel.ts:31`) and the v1
  renderer, plus their tests. It exists only to position carousel images inside blog bodies; after
  AE-0422 nothing reads it.
- **Dead frontend files:** `ImageGenModal`, `SeoPreview`, `AccessibilityChecker`,
  `KeyboardShortcutsHelp`, the `BlogPostFilters` *component* (not the live type of the same name),
  `useAccessibilityCheck`, `useSeoAnalysis`, `useEditorShortcuts`, the v1
  `useCarouselProject`/`useCarouselProjects`/`useCarouselBlog*`/`useCarouselDesign` hook family in
  `blog/hooks/use-carousel-blog.ts`, `mapProjectToBlogPostCard`, the orphan `blog/hooks/index.ts`
  barrel, `constants/editor-shortcuts.ts`, `constants/seo.ts`, `constants/blog.ts::CAROUSEL_SLIDE_*`,
  `fetchBlogWithDesignCombined`, the v1 blog types in `schemas/carousel.ts`, and the v1 query helpers
  in `modules/carousel-presentation/queries.ts` (keep `carouselProjectOptions`). These are already
  dead or become dead once AE-0422 removes slide images; Knip's `scripts/dead-code-baseline.json`
  confirms the first group. `public-blog.ts`, `public-blog-cards.ts` and `blog-post-content.tsx` are
  rewritten for v2, not deleted.
- **Dead backend files:** `nodes/content/blog_cleanup.py` and the whole unreferenced
  `nodes/content/` package (only a unit test imports it). The carousel→blog dual-write
  **upsert** (`sync_carousel_blog_post`) is removed in **AE-0422**, because it writes v1 markdown and
  `status='published'` on every carousel save and would clobber the v2 document; the delete-time
  `detach_carousel_blog_posts` (published→draft before the FK `SET NULL`) is retained. The
  carousel's distribution helpers (`blog_composition.py`, `editorial_distribution_blog.py`) and the
  `blog_markdown`/`blog_translations` columns are **live** for the editorial distribution pack and
  stay.
- **Guard:** delete the `dead-code-baseline.json` entries for the removed symbols so Knip fails if
  they come back, and add a grep/static test asserting no `blog_image_map` and no removed v1
  renderer symbol remains in `src/`.

### Rollout

- **A (AE-0422) ships first and alone:** the frontend stops injecting carousel slides into blog
  bodies; the stale slide specs are retired; every published carousel-origin post is hidden.
- **B (AE-0423) before C and D:** document model + one-shot v1→v2 cutover command + explicit deploy
  step + public render. After `--verify`, v2 is the only persisted shape; no v1 write path remains
  (the temporary read fail-safe goes away in AE-0428).
- **C (AE-0424) and D (AE-0425) in parallel:** editor (sections, images, PT/EN toggle, review +
  schedule), and writer + images (section count from the carousel's `slide_count`).
- **E (AE-0426) after D:** rebuild the hidden posts as drafts via the new pipeline.
- **F (AE-0428) after A/B/C; may run before or after E:** delete the dead blog-v1 files and drop
  `blog_image_map` end-to-end;
  remove their Knip baseline entries and add the no-regression guard.

### Consequences

- **Good:** the post owns its structure, voice and images; F-01/F-02/F-03/F-06/F-07/F-08/F-09/
  F-10/F-11/F-12/F-13/F-15 are addressed by the model rather than patches; the public/private
  boundary (ADR-0013), the single store (ADR-0006/0009/0011) and the frozen carousel pipeline
  (ADR-0007) are preserved; the cutover is one-shot, idempotent and reversible at the data level;
  PT/EN are first-class in the document; the dead v1 code and `blog_image_map` are deleted rather
  than carried.
- **Bad:** a new writer agent + prompts + image cost per post; a one-shot data cutover to run on
  deploy (all rows become v2 before the new code serves, so there is no partial-state window; a
  failed verify aborts the deploy and a temporary read fail-safe keeps reads up); A briefly renders
  legacy markdown (without slides) until B's cutover; sections are not queryable relationally
  (acceptable for a per-post document, ADR-0006).
- **Neutral:** the review/schedule state machine and endpoints already exist and are kept; the change
  is that they now have editor controls and are covered by feature tests. `blog_image_map` and the
  dead blog-v1 files are deleted, which removes the old positional-image failure class instead of
  preserving it.

### Confirmation

Backend `.feature` tests assert: the one-shot cutover migrates every PT body **and every
`content.translations` language** idempotently, `--verify` reports zero non-v2 rows, and `--rollback`
re-joins sections with identical body bytes; the strict parser rejects non-v2 writes while the read
fail-safe serves a non-migrated row as text-only v2 (never a 500, never a slide); a generated post is
always a `draft`; the writer body scores `>= 70` or gets exactly one rewrite; a repeated sentence is
detected; a failed image leaves `image = null` and records an error without failing the draft; a
restart mid-generation is reaped to `failed`/recoverable and can be retried without a duplicate row;
`PUT` appends a version snapshot; `ai-suggest` never returns a fenced envelope; a carousel-origin
generation produces exactly `project.slide_count` validated sections and `slide_count + 1` image
slots (stored images may be fewer on failure); the schedule/review transitions enforce their status
guards and an edit resets approval. Frontend
`.feature` tests assert: the public page renders each section with its own image + non-empty alt and
never a carousel slide URL (no `/slide-images/`); reordering a section keeps its image; the PT/EN
buttons switch the edited and rendered document (EN falls back to PT when absent); the editor guards
unsaved changes; Submit review / Approve / Schedule / Publish / Unpublish work; the design payload
no longer contains `blog_image_map`.

## More Information

- Companion design: [`docs/architecture/blog-post-document-model.md`](../architecture/blog-post-document-model.md).
- QA evidence: `~/alter-ego-qa/2026-10-18-blog/REPORT.md` (F-01..F-15).
- Tickets: AE-0422 (A), AE-0423 (B), AE-0424 (C), AE-0425 (D), AE-0426 (E), AE-0428 (F);
  epic AE-0427.
- Related ADRs:
  - **Amends/refines ADR-0006** (JSONB rich content): the blog document now has an explicit
    versioned shape `blog.v2` (one shape; no v1 read path), replacing the "TipTap `type: doc`"
    assumption.
  - **Enforces ADR-0003** (persona-driven content) for the blog body, which it previously did not
    cover.
  - **Preserves ADR-0011** (`distribution` home) and **ADR-0013** (public/private split, uniform
    404, lean payload).
  - **Honours ADR-0009** (modular monolith: writer placed in `application/` behind a Protocol, new
    agent facade per ADR-0016), **ADR-0014** (tiered models), **ADR-0007/0021** (carousel pipeline
    frozen). It does not change **ADR-0012**: schema migrations stay on Alembic; this JSONB rewrite
    runs as its own command because prod's Alembic chain/stamp is still being reconciled (AE-0207).
- Possible follow-ups (not in scope): owner photo upload (`source: "upload"`), a `modules/blog`
  bounded-context extraction, RSS/social distribution of the new document.

## Tags

#blog #content-model #jsonb #persona #images #editor #i18n #scheduling #migration #cleanup #adr
