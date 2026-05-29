# Carousel Pipeline Consolidation Plan

**Status:** In progress (ADR-007 accepted)
**Date:** 2026-05-24
**Scope:** Unify the editorial LangGraph workflow and the legacy carousel generation pipeline into a single end-to-end system with per-phase human review, feedback-driven revision, DeepAgents orchestration, strict blog visibility, and removal of all legacy endpoints.

---

## 1. Purpose

Alter-Ego currently runs two carousel pipelines in parallel:

| Pipeline | Entry points | Orchestration | Progress |
|----------|--------------|---------------|----------|
| **Editorial workflow** | `/api/carousels/{id}/workflow/*` | Raw LangGraph (`CarouselWorkflowEngine`) with `interrupt()` gates | Minimal SSE (`phase` + `phase_status`); heavy work on `/workflow/resume` |
| **Legacy generation** | `/api/carousels/{id}/generate`, `/stream`, `/status`, `/resume` | `CarouselAgent` → full `build_graph()` pipeline | Rich `phase_progress` SSE |

The frontend bridges them: editorial gates drive approvals while `EditorialWorkflowProgress` polls the legacy stream for design/image detail. That bridge caused the infinite `/stream` loop, stuck research approvals, empty review panels, and inconsistent artifact generation.

This plan consolidates everything into **one editorial pipeline** that:

- Renders phase artifacts and accepts structured feedback in the create workspace for every human gate.
- Uses **DeepAgents** for orchestration and subagent spawning, with raw LangGraph nodes for deterministic work.
- **Refactors** `skills/carousel-pipeline/` into `_shared/` standards + phase-scoped skills for progressive disclosure (preserves all content contracts, design rules, and anti-patterns from the current monolith).
- Delivers workflow status updates to the frontend via **SSE as primary transport**; HTTP polling of `/workflow/state` is **fallback only** when SSE fails.
- Separates **workspace preview** from **public blog** so unpublished content is never visible on public routes—even to admins.
- Removes legacy endpoints and all client/server dependencies on them.
- Fixes known workflow bugs as part of the same refactor so the create → review → publish path works end-to-end.

---

## 2. Current Defects to Resolve in Consolidation

These are not deferred; they are fixed by the target design.

### 2.1 Workflow engine

- **Reject routes to END:** Conditional edges send `_ROUTE_RETRY → END`, leaving the graph at a terminal checkpoint while UI still shows `awaiting_human`. Partial recovery exists via `_needs_gate_reopen`; the fix is to loop retries inside the graph instead of exiting.
- **Heavy synchronous resume:** `_prepare_phase_before_resume` runs outline generation, content drafting, design tokens, and image generation *before* `interrupt()` resumes, blocking `POST /workflow/resume` for tens of seconds and risking client timeouts.
- **Approve-before-generate ordering:** Research approval triggers outline generation in the service layer instead of inside the outline phase node, so state and interrupts are out of sync.
- **Missing artifacts at gates:** Content/design phases can reach `awaiting_human` with empty `slide_drafts` or `design_applied=false` because generation runs at the wrong time.
- **Feedback is recorded but ignored:** Resume accepts `feedback`; reject hardcodes `"Needs revision"`. Nothing replays feedback into agent prompts or triggers regeneration.

### 2.2 Dual progress systems

- Editorial SSE emits only coarse phase changes.
- Legacy stream emits granular `phase_progress` but only when the legacy pipeline is running—which editorial workflow never starts—so the UI polls idle `pending` status indefinitely.

### 2.3 Blog visibility

- Public listing filters on `is_public=true` (correct for anonymous users).
- Media routes use `assert_carousel_public_or_editor`, which allows **any authenticated admin/editor** to load draft blog, design, and images via the same URLs the public blog page uses.
- The public blog page at `/blog/{id}` calls unauthenticated fetch helpers; when an admin session cookie is present, draft carousels render on the public blog layout with admin controls.
- `final_review` approval and `_sync_project_phase` set `is_public=true` automatically, conflating editorial sign-off with public release.

### 2.4 Legacy coupling

- Caption generation (`POST /caption`) calls `execute_pipeline`, running the entire legacy graph for a caption.
- RAG tool `generate_carousel` invokes the same legacy pipeline.
- `carousel_orchestrator/`, `application/services/carousel/graph.py`, and `subagent.py` duplicate logic now partially bridged by `editorial_visual_pipeline.py`.

---

## 3. Target Architecture

### 3.1 Single pipeline, single API surface

All carousel AI work flows through the editorial workflow API:

| Concern | Unified endpoint |
|---------|------------------|
| Start workflow | `POST /api/carousels/{id}/workflow/start` |
| Current state | `GET /api/carousels/{id}/workflow/state` |
| Human decision + feedback | `POST /api/carousels/{id}/workflow/resume` |
| Progress + artifacts stream | `GET /api/carousels/{id}/workflow/stream` (extended) |
| Workspace preview (blog/design/images) | `GET /api/carousels/{id}/preview/*` (authenticated, never public-cacheable) |
| Public release | `POST /api/carousels/{id}/publish` (explicit, sets `is_public`) |

**Removed entirely:** `/generate`, `/stream`, `/status`, `/resume` on carousels, plus `CarouselAgent.execute_pipeline` / `stream_pipeline` as public API paths. Internal deterministic helpers (`run_design`, `run_images`, etc.) remain as library functions invoked from workflow nodes—not as a second graph.

### 3.2 Layering

```
┌─────────────────────────────────────────────────────────────┐
│  Frontend: Create workspace (EditorialWorkflowPanel)        │
│  - Phase review panels + feedback forms                     │
│  - Unified workflow SSE for progress + artifacts            │
│  - Workspace preview (not public /blog)                     │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│  EditorialWorkflowService                                   │
│  - Thin coordination: DB sync, events, Langfuse, notifications│
│  - No heavy generation in resume path                         │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│  CarouselEditorialOrchestrator (Deep Agent)                 │
│  - Planning, phase transitions, interrupt() gates           │
│  - Spawns phase subagents via `task` tool                   │
└────────────┬─────────────────────────────┬────────────────────┘
             │                             │
   ┌─────────▼─────────┐         ┌─────────▼─────────┐
   │ Phase subagents   │         │ Deterministic     │
   │ (DeepAgents       │         │ LangGraph nodes   │
   │  CompiledSubAgent)│         │ (design, images,  │
   │                   │         │  PDF, blog export,│
   │ research, outline,│         │  quality scoring) │
   │ content, caption  │         │                   │
   └───────────────────┘         └───────────────────┘
             │
   ┌─────────▼─────────────────────────────────────────┐
   │ Existing agents (wrapped, not rewritten):           │
   │ SourceSynthesisAgent, OutlineAgent,                 │
   │ ContentDraftAgent, PersonaAgent, QualityAgent       │
   └─────────────────────────────────────────────────────┘
```

### 3.3 DeepAgents usage (implementation model)

Per ADR-002 and `docs/architecture/langchain-deep-agents-guide.md`:

**Orchestrator (`CarouselEditorialOrchestrator`)**

- Built with `create_deep_agent` from the `deepagents` package.
- Owns the seven-phase state machine: `brief → research → outline → content → design → images → final_review`.
- Uses built-in `write_todos` for visible planning steps streamed to the UI (e.g., "Synthesizing 3 source materials", "Drafting slide 4/8").
- Every human gate uses LangGraph `interrupt()` with a typed payload; the orchestrator never wraps `interrupt()` in bare `try/except` (re-raise `GraphInterrupt`).
- Checkpointer: one thread per `project_id` (Postgres or SQLite depending on environment), replacing the editorial/legacy split.

**Phase subagents (CompiledSubAgent registrations)**

Each subagent wraps an existing agent module as a `{"name", "description", "runnable"}` spec—the same pattern already started in `application/services/carousel/subagent.py`, but scoped to **one phase** instead of the full pipeline:

| Subagent name | Wraps | Invoked when |
|---------------|-------|--------------|
| `research_synthesizer` | `SourceSynthesisAgent` | Research phase enters (after brief) or research revision requested |
| `outline_planner` | `OutlineAgent` | Outline phase enters or outline revision requested |
| `content_drafter` | `ContentDraftAgent` (+ optional parallel spawn per slide) | Content phase enters or content revision requested |
| `caption_writer` | Dedicated caption prompt (extracted from legacy export node) | Final review prep or publish panel refresh |

Subagents receive structured JSON input (topic, audience, sources, prior artifacts, **reviewer feedback**, persona id) and return structured JSON output merged into `CarouselWorkflowState`. The orchestrator reads the last `AIMessage` summary for Langfuse tracing.

**Deterministic nodes (raw LangGraph, not Deep Agents)**

These stay as plain async functions in the compiled graph—no LLM planning needed:

| Node | Responsibility | Existing code reused |
|------|----------------|----------------------|
| `apply_design` | Template tokens, hero palette | `editorial_visual_pipeline.apply_design_tokens`, `run_design` |
| `render_images` | Slide images via registry | `generate_carousel_images`, `run_images` |
| `export_pdf` | LinkedIn PDFs | Legacy export node |
| `compose_blog` | Markdown blog from slides | Legacy blog composition node |
| `score_quality` | Rubric evaluation | `QualityAgent`, `QualityEvaluationService` |
| `sync_slides` | Persist outline → DB slides | `ensure_slides_from_outline` |

**Persona enforcement**

- `PersonaAgent.enforce()` runs as a deterministic gate after content drafting and before the content review interrupt—not as a separate Deep Agent.
- Voice match score and forbidden phrases are included in the content review interrupt payload; scores below threshold block approval in the UI.

**RAG / chat integration**

- Replace `generate_carousel` tool implementation: create project via API, call `workflow/start`, return workflow state summary—not `execute_pipeline`.
- Register `CarouselEditorialOrchestrator` as a `CompiledSubAgent` on `RAGAgent` for conversational carousel creation (not on `AlterEgoAgent`), using the same checkpointer thread as the create workspace.

**Langfuse**

- All subagent and deterministic node invocations use `get_langfuse_handler()` with metadata: `project_id`, `phase`, `agent_name`, `user_id`, `content_type=carousel`.
- Human review events link to the active trace via `record_human_review`.

### 3.4 Skills, standards, and progressive disclosure

The project’s `skills/carousel-pipeline/` is **not** removed. It is the canonical home for carousel content standards. The consolidation **refactors** how those standards are loaded and consumed — it does not discard them.

#### Why the current setup fails progressive disclosure

Today `RAGAgent` registers `skills=["skills/carousel-pipeline"]` on the **parent** `create_deep_agent` call while also attaching a **monolithic** legacy subagent. That loads the entire 7-phase playbook (~500 lines across `SKILL.md` + `workflow.md`) into the parent context up front, alongside a runnable that runs the full legacy graph. Skills and subagents are different mechanisms; the monolith skill is not a subagent.

#### Skills ≠ subagents

| Mechanism | Purpose | Executes code? |
|-----------|---------|----------------|
| `skills/` (`SKILL.md`, `_shared/*.md`) | Behavior instructions, contracts, anti-patterns | No — loaded into LLM context |
| `CompiledSubAgent` | Isolated runnable invoked via `task` | Yes — wraps LangGraph + Python agents |
| `agents/prompts/carousel/` | Parameterized runtime templates | Yes — rendered and sent to LLM |
| Python agents + renderers | Generation and validation | Yes — enforce contracts in code |

Phase subagents **use** phase skills; they are not **replaced by** them.

#### Standards that must be preserved (from current monolith)

Extract from `skills/carousel-pipeline/SKILL.md` and `workflow.md` into `_shared/` — do not lose any of the following:

| File (target) | Content migrated |
|---------------|------------------|
| `_shared/critical-rules.md` | Language (pt-BR/en), fact-checking, bilingual storage, fail-loudly, user sources authoritative, prerequisites |
| `_shared/anti-patterns.md` | Full symptom / root cause / fix table (topic drift, speech bubbles, stub slides, CTA dimensions, em dashes, etc.) |
| `_shared/content-contracts.md` | Content JSON return shape; slide types (`intro`, `content`, `closing`, `cta`); `features`, `stats`, `insight` extras; one structured extra per slide; tool vocabulary |
| `_shared/text-formatting.md` | Em-dash ban; `**bold**` vs `` `code` ``; heading accent highlights (max 2 words); paragraph length |
| `_shared/design-system.md` | Theme palettes and brand detection; design token JSON schema; typography table (1080×1350); `.feature-grid` CSS; intro footer flex; progress segments |
| `_shared/image-generation.md` | Scene-only `image_prompt` rules; Gemini wrapper template; intro + content slides only; rate limiting |
| `_shared/export-and-caption.md` | Playwright 1080×1350 export; caption structure (hook, CTA, hashtags); blog markdown rules |

Phase skills in `phases/` contain **phase-specific workflow** (research dispatch, title criteria, HITL expectations) and **reference** the relevant `_shared/` files — they do not duplicate the full monolith.

#### Target directory layout

```
skills/carousel-pipeline/
├── SKILL.md                      # Slim entry: triggers, purpose, delegate to phase subagents
├── bmad-skill-manifest.yaml      # Updated for editorial workflow + phase skills
├── _shared/                      # Canonical standards (preserved from monolith)
│   ├── critical-rules.md
│   ├── anti-patterns.md
│   ├── content-contracts.md
│   ├── text-formatting.md
│   ├── design-system.md
│   ├── image-generation.md
│   └── export-and-caption.md
└── phases/
    ├── research/SKILL.md         # Source priority, ResearchSource fields, parallel dispatch
    ├── outline/SKILL.md          # Title criteria, outline shape
    ├── content/SKILL.md          # Slide structure, JSON contract refs
    ├── design/SKILL.md           # Token generation, theme resolution
    ├── images/SKILL.md           # Generation scope, prompt rules refs
    └── final-review/SKILL.md     # Blog bundle, caption, quality checklist

skills/carousel-refinement/       # Keep — maps to refinement tools
└── SKILL.md
```

After migration, `workflow.md` is deprecated (replaced by `_shared/` + `phases/`); git history retains the original.

#### Three-layer alignment

| Layer | Consumer | Update order when standards change |
|-------|----------|-----------------------------------|
| `skills/carousel-pipeline/_shared/` | Deep Agent subagents, developers, QA | **First** — canonical spec |
| `agents/prompts/carousel/v1/` | Python agents at runtime | Second — Jinja/YAML must match `_shared/` |
| Python validators / HTML renderers / `CarouselTemplateBuilder` | All paths (API + chat) | Third — enforce contracts in code |

The create-workspace API path does not load the full skill on every request. Graph nodes call Python agents whose prompts align with `_shared/`. Phase skills load when a subagent runnable is constructed or when chat delegates via `task`.

#### Progressive disclosure rules

| Agent | Skills loaded |
|-------|---------------|
| `RAGAgent` (parent) | **None** for carousel — remove `skills=["skills/carousel-pipeline"]` |
| `AlterEgoAgent` | None (unchanged) |
| `research_synthesizer` subagent | `phases/research` + `_shared/critical-rules`, `_shared/anti-patterns` (research subset) |
| `outline_planner` subagent | `phases/outline` + `_shared/critical-rules`, `_shared/text-formatting` |
| `content_drafter` subagent | `phases/content` + `_shared/content-contracts`, `_shared/text-formatting`, `_shared/anti-patterns` |
| `design` deterministic node context | `_shared/design-system` (via prompts, not full skill stack) |
| `images` deterministic node context | `_shared/image-generation` |
| `final-review` / caption | `phases/final-review` + `_shared/export-and-caption` |
| Refinement tools (chat) | `skills/carousel-refinement` |

Each phase loads **only** its phase skill plus the minimum `_shared/` files needed for that phase — never the full 7-phase document at initialization.

#### Subagent ↔ skill ↔ Python agent mapping

| Subagent / node | Phase skill | Python execution | Shared standards |
|-----------------|-------------|------------------|------------------|
| `research_synthesizer` | `phases/research` | `SourceSynthesisAgent` | critical-rules, anti-patterns |
| `outline_planner` | `phases/outline` | `OutlineAgent` | critical-rules, text-formatting |
| `content_drafter` | `phases/content` | `ContentDraftAgent`, `PersonaAgent.enforce` | content-contracts, text-formatting, anti-patterns |
| `apply_design` (node) | `phases/design` | `apply_design_tokens`, `run_design` | design-system |
| `render_images` (node) | `phases/images` | `generate_carousel_images` | image-generation |
| `compose_blog` + `score_quality` | `phases/final-review` | blog node, `QualityAgent` | export-and-caption, content-contracts |
| `caption_writer` | `phases/final-review` | caption prompt / `run_caption` | export-and-caption |

---

## 4. Workflow State Machine (Revised)

### 4.1 Phase lifecycle (uniform for all gates)

Each phase follows the same internal loop:

1. **Enter phase** → set `phase_status: in_progress`, emit workflow event.
2. **Generate** → orchestrator spawns the phase subagent or runs deterministic nodes; stream granular progress into `phase_progress` on the project row and via SSE.
3. **Review interrupt** → set `phase_status: awaiting_human`, payload includes all artifacts required for UI review.
4. **Human response** via `/workflow/resume`:
   - **Approve** → set phase approved flag, advance to next phase (generation for next phase starts *after* transition, inside that phase's enter step—not in the resume handler).
   - **Revise** (replaces bare "reject") → store feedback in `phase_feedback[phase]`, increment `revision_count`, loop to step 2 without hitting END.
5. **Revision cap** → configurable maximum (default 5); after cap, force escalation notification to admin.

Retry edges change from `_ROUTE_RETRY → END` to `_ROUTE_RETRY → same_phase_node`.

### 4.2 Phase-by-phase specification

#### Brief

- **Artifacts shown:** Topic, audience, niche, brief text, attached source materials list.
- **Feedback use:** Adjust brief fields and source attachments; re-validates without AI call when only metadata changes.
- **Generation:** Validation only; auto-advances to research when materials gate satisfied.

#### Research

- **Artifacts shown:** `research_findings[]` with source title, URL/type, key points, confidence.
- **Feedback use:** Passed to `research_synthesizer` subagent as revision instructions; optional source add/remove triggers re-synthesis on listed sources only.
- **Generation:** `SourceSynthesisAgent` via subagent at phase enter—not on prior phase approval.

#### Outline

- **Artifacts shown:** Ordered slide list with title, key points, slide type, estimated narrative arc summary.
- **Feedback use:** Injected into `outline_planner`; supports "merge slides 3–4", "change angle", etc.
- **Generation:** `OutlineAgent` at phase enter.

#### Content

- **Artifacts shown:** Per-slide `draft_text`, persona voice score, forbidden phrase warnings, side-by-side outline reference.
- **Feedback use:** Per-slide or global feedback; parallel subagent respawn for flagged slides only.
- **Generation:** `ContentDraftAgent` (+ `PersonaAgent.enforce`) at phase enter; persists drafts to state and DB.

#### Design

- **Artifacts shown:** Live carousel preview (template tokens, typography, colors), before/after token diff, slide layout thumbnails.
- **Feedback use:** Natural language ("warmer palette", "larger headline") mapped to template parameter adjustments; re-runs `apply_design` deterministically.
- **Generation:** `apply_design_tokens` + `run_design` at phase enter—not on content approval.

#### Images

- **Artifacts shown:** Rendered slide images (authenticated preview URLs), generation metadata (provider, prompt summary), failed slide indicators.
- **Feedback use:** Per-slide regeneration instructions; re-invokes `render_images` for selected slides only.
- **Generation:** `generate_carousel_images` at phase enter—not on design approval.

#### Final review (blog + carousel bundle)

- **Artifacts shown:**
  - Full carousel preview (slides + design).
  - Blog markdown preview (both locales if available).
  - Rubric scores from `QualityAgent`.
  - Instagram caption draft and LinkedIn post snippets.
  - Checklist: persona score, forbidden phrases, materials attribution.
- **Feedback use:** Routes revision to the appropriate earlier phase (research, outline, content, design, images) based on feedback classification—either explicit user selection ("send back to content") or automatic routing via a lightweight classifier in `FeedbackLearningLoop.classify_correction`.
- **On approve:** Sets workflow status to `approved_for_publish`, `current_phase: final_review`, `quality_passed: true`. Does **not** set `is_public`.
- **Publish:** Separate explicit action via `POST /publish` or publish panel after final approval.

### 4.3 Resume handler slim-down

`EditorialWorkflowService.resume_workflow` becomes:

1. Validate reviewer access and optimistic lock.
2. Persist human input (`action`, `feedback`, optional structured edits).
3. Call `CarouselEditorialOrchestrator.resume(project_id, human_input)`—no `_prepare_phase_before_resume`.
4. Sync DB phase fields, emit events, record Langfuse review.
5. Return full state including artifacts.

All generation moves into graph nodes triggered by phase entry or revision loops.

---

## 5. Unified Progress Streaming

Extend `GET /workflow/stream` to replace legacy `/stream` entirely.

### 5.1 Event types

| SSE event | Payload | When |
|-----------|---------|------|
| `phase_change` | `phase`, `phase_status` | Phase transition |
| `progress` | `phase`, `step`, `message`, `percent`, `slide_index?` | Subagent or deterministic node progress |
| `artifact` | `phase`, `artifact_type`, `data` | Incremental artifact updates (e.g., slide draft ready) |
| `review_required` | Full interrupt payload | Gate opened |
| `error` | `phase`, `message`, `recoverable` | Failure with retry hint |

Events are sourced from:

- Deep Agent todo updates (planning steps).
- Deterministic node callbacks (image 3/8 rendered).
- Graph interrupt payloads.

### 5.2 Persistence

- `carousel_projects.phase_progress` JSONB stores the latest progress snapshot for reload resilience (same shape legacy stream used, now written by editorial nodes).
- Frontend reads persisted snapshot on mount, then subscribes to SSE for live updates.

### 5.3 Frontend consumption — SSE primary, polling fallback

**Current problem:** `useEditorialWorkflow` polls `GET /workflow/state` every 3 seconds while `loading === true`, alongside a partial SSE listener. This duplicates transport, increases load, and masked the legacy stream loop issue.

**Target transport model:**

| Priority | Mechanism | When |
|----------|-----------|------|
| **Primary** | `EventSource` on `GET /api/carousels/{id}/workflow/stream` | Always while create workspace is mounted |
| **Initial hydrate** | Single `GET /workflow/state` on mount | Once per page load to restore checkpoint before SSE connects |
| **Fallback** | Interval poll `GET /workflow/state` | Only when SSE disconnects or errors; backoff 5s → 10s → 30s; stop when SSE reconnects |
| **Removed** | Legacy `/stream`, `/status` | Deleted with legacy pipeline |
| **Removed** | Unconditional poll during `loading` | Replaced by SSE `progress`, `phase_change`, `review_required` events |

**Hook responsibilities (`useEditorialWorkflow`):**

1. On mount: one state fetch → open SSE.
2. On SSE `phase_change` / `progress` / `artifact` / `review_required` / `error`: merge into local state (same fields today).
3. On SSE `error` or `onerror`: set `transportMode: "polling-fallback"`, start guarded interval poll.
4. On SSE reconnect: clear fallback interval, set `transportMode: "sse"`.
5. During `awaiting_human`: SSE stays open for notifications but **no** progress polling loop.

**UI indicator (optional):** subtle degraded-mode badge when fallback polling is active.

### 5.4 Backend SSE contract requirements

- Stream must emit `review_required` when interrupt opens so UI updates without poll.
- Stream must emit terminal `phase_change` when resume completes so `loading` clears without poll.
- Keepalive comments every 30s (existing) to detect dead connections client-side.
- Auth via session cookie on `EventSource` (`withCredentials: true`).

---

## 6. Per-Phase Review UI and Feedback

### 6.1 Create workspace panel structure

Replace the current approve/reject button pair with a **phase review shell** used at every gate:

| Region | Content |
|--------|---------|
| **Progress strip** | Unified SSE progress (Section 5) |
| **Artifact viewer** | Phase-specific renderer (extends `EditorialPhaseReview`) |
| **Feedback composer** | Required on revise; optional on approve (minor notes) |
| **Structured edits** | Where applicable: inline slide text edit, outline reorder, source toggle |
| **Actions** | Approve · Request revision · (Send back to \<phase\> on final review) |

### 6.2 Phase renderers (complete coverage)

| Phase | Renderer |
|-------|----------|
| Brief | Materials gate + brief summary (existing `BriefMaterialsGate`) |
| Research | Source cards with key points (existing partial) |
| Outline | Ordered slide outline with drag reorder sending structured diff on revise |
| Content | Per-slide TipTap read-only or editable preview with persona badge |
| Design | Embedded `CarouselPreview` with design tokens |
| Images | Slide filmstrip with lightbox; failed slides highlighted |
| Final review | Tabbed: Carousel · Blog · Caption · Quality scores |

`final_review` currently returns `null` from `EditorialPhaseReview`—this is a required addition.

### 6.3 Feedback payload schema

Extend `EditorialWorkflowResumeRequest`:

| Field | Purpose |
|-------|---------|
| `action` | `approve` \| `revise` |
| `feedback` | Free-text instructions (sanitized via `sanitize_llm_input`) |
| `structured_feedback` | Phase-specific JSON (slide edits, outline order, target_phase for final review) |
| `expected_version` | Optimistic lock token |

Backend merges into `CarouselWorkflowState.phase_feedback` and passes to subagent on regeneration.

### 6.4 Feedback learning persistence

Upgrade `FeedbackLearningLoop` from in-memory dict to Postgres storage (corrections table keyed by `persona_id`, `project_id`, `phase`). On revision, `get_relevant_examples()` feeds few-shot examples into subagent prompts. Corrections recorded when user edits differ from AI output in structured edit fields.

---

## 7. Blog Pre-Publish Review and Visibility Model

### 7.1 Visibility rules (strict)

| Route / resource | Anonymous | Authenticated editor/admin |
|------------------|-----------|----------------------------|
| Homepage carousel list | `is_public=true` only | All owned projects in dashboard; public list unchanged |
| `/blog/{id}` (public blog layout) | `is_public=true` only | **`is_public=true` only** — same as anonymous |
| `/create/{id}/preview/blog` | 401 | Draft + approved-for-publish preview |
| `/api/carousels/{id}/blog` (legacy media path) | 404 unless public | **404 unless public** |
| `/api/carousels/{id}/preview/blog` | 401 | Authenticated project access |

Replace `assert_carousel_public_or_editor` with:

- `assert_carousel_public` — for all former public media/blog/design/image routes.
- `assert_carousel_project_access` — for new `/preview/*` routes (owner, editor, admin with project access).

Remove the `current_phase == published` bypass in the public guard; publication is solely `is_public`.

### 7.2 Admin panel relocation

- Remove `BlogPostAdminPanel` from public `/blog/{id}` page.
- Admin actions (edit blog, publish, delete) live in:
  - Create workspace final review tab.
  - Publish panel (`/create/{id}/publish`).
  - Dashboard blog-posts list.

Public blog pages become read-only for everyone.

### 7.3 Publish sequence

1. Workflow reaches `final_review` → human reviews bundled artifacts in create workspace.
2. Approve → `approved_for_publish` (workflow complete, not public).
3. Editor opens publish panel → reviews caption, Instagram/LinkedIn copy, PDF.
4. Explicit **Publish to site** → `POST /publish` sets `is_public=true`, `current_phase=published`.
5. Public `/blog/{id}` becomes accessible.

Remove automatic `is_public=true` from `_sync_project_phase` on workflow phase `published`; only the publish endpoint sets it.

### 7.4 Blog generation timing

- Blog markdown composed during **final review enter** (deterministic `compose_blog` node), after images approved.
- Both locales generated if project supports i18n.
- Final review interrupt payload includes `blog_markdown_pt`, `blog_markdown_en`, preview URLs pointing at `/preview/` routes.

---

## 8. Legacy Removal Inventory

### 8.1 Backend routes to delete

| Route | File |
|-------|------|
| `POST /{id}/generate` | `api/routes/carousels/generation.py` |
| `GET /{id}/stream` | same |
| `GET /{id}/status` | same |
| `POST /{id}/resume` | same |

Remove router registration from `api/routes/carousels/__init__.py`. Delete or gut `generation.py`.

### 8.2 Backend modules to delete or fold

| Module | Disposition |
|--------|-------------|
| `agents/carousel_orchestrator/` | Delete after logic migrated to phase subagents + deterministic nodes |
| `application/services/carousel/graph.py` (legacy `build_graph`) | Delete |
| `application/services/carousel/subagent.py` (full-pipeline wrapper) | Replace with per-phase subagent registry + phase skill paths |
| `domain/protocols/carousel.py` → `CarouselAgent` | Remove protocol; keep repository protocol |
| `api/routes/carousels/publishing.py` → `generate_caption` via `execute_pipeline` | Rewrite to read caption from state or invoke `caption_writer` subagent only |

### 8.3 Frontend removal

| Artifact | Disposition |
|----------|-------------|
| `use-carousel.ts` stream/status/generate hooks | Delete |
| `use-carousel-stream.test.ts` | Delete |
| `editorial-workflow-progress.tsx` legacy stream import | Use workflow stream only |
| `CAROUSEL_GENERATE`, `CAROUSEL_STREAM`, `CAROUSEL_STATUS`, `CAROUSEL_RESUME` | Remove from `constants/api.ts` |

### 8.4 RAG tool and skills

| Artifact | Disposition |
|----------|-------------|
| `application/tools/carousel/generate_carousel.py` | Call editorial workflow start + return state |
| `RAGAgent` `skills=["skills/carousel-pipeline"]` on parent | **Remove** — delegate to phase subagents with scoped skills |
| `skills/carousel-pipeline/SKILL.md` (monolith) | **Refactor** into slim entry + `_shared/` + `phases/` |
| `skills/carousel-pipeline/workflow.md` | **Migrate** to `_shared/` + `phases/`; deprecate file |
| `skills/carousel-refinement/` | **Keep** — aligned with refinement tools |
| `bmad-skill-manifest.yaml` | **Update** — editorial workflow triggers, phase skill paths |

---

## 9. API and Schema Extensions

### 9.1 `CarouselWorkflowState` additions

| Field | Type | Purpose |
|-------|------|---------|
| `phase_feedback` | `dict[phase, FeedbackRecord]` | Cumulative reviewer feedback per phase |
| `revision_count` | `dict[phase, int]` | Revision tracking |
| `phase_progress` | `PhaseProgressSnapshot` | Latest granular progress (mirrors DB column) |
| `blog_markdown_pt` / `blog_markdown_en` | `str \| null` | Final review artifacts |
| `caption` | `str \| null` | Final review artifact |
| `persona_scores` | `dict` | Per-slide voice match |
| `workflow_status` | enum | `draft` \| `in_review` \| `approved_for_publish` \| `published` |

### 9.2 New preview routes

| Route | Response |
|-------|----------|
| `GET /carousels/{id}/preview/blog/{lang}` | Blog markdown + metadata |
| `GET /carousels/{id}/preview/design/{lang}` | Design tokens (same schema as public) |
| `GET /carousels/{id}/preview/images/{slide}` | Image file stream |

All require editor authentication and project access; never cached publicly.

### 9.3 Caption route rewrite

`POST /carousels/{id}/caption` reads caption from workflow state if present; otherwise triggers `caption_writer` subagent asynchronously and returns result—never the full pipeline.

---

## 10. Event, Board, and Notification Alignment

- Workflow board (`/api/workflow/board`) maps `workflow_status` and `phase_status` from unified state—remove legacy `CarouselStatus` enum dependency.
- Notifications on `review_required` include deep link to create workspace with phase query param.
- Phase approval/revision events carry feedback excerpt for audit log (`workflow_audit_log`).

---

## 11. Implementation Sequence

Work proceeds in dependency order. **Section 16** defines tasks with acceptance criteria; each task maps to Gherkin scenarios in **Section 15**. Do not mark a stage complete until all linked scenarios pass.

| Stage | Focus | Task IDs |
|-------|-------|----------|
| A | Skills refactor + engine core | CP-001 – CP-010, CP-006b |
| B | Visibility + preview routes | CP-011 – CP-015 |
| C | Review UI + feedback UX | CP-016 – CP-022 |
| D | Legacy removal + RAG | CP-023 – CP-028 |
| E | E2E verification + docs | CP-029 – CP-031 |

Summary (detail in §16):

- **Stage A:** Skills migration, graph retry loops, orchestrator, unified SSE, **SSE-primary frontend hook**, feedback persistence, RAG skill scoping
- **Stage B:** Preview routes, public guards, publish separation, admin panel relocation
- **Stage C:** Phase review UI, feedback composer, progress fix, approve/revise wiring
- **Stage D:** Delete legacy routes/modules, caption/RAG rewrite, frontend hook removal
- **Stage E:** Full scenario suite green, ADR accepted, docs updated

---

## 12. End-to-End Flow (Target)

```
Editor creates project
    → Materials gate (brief + sources)
    → POST /workflow/start
    → [research: synthesize → review → approve/revise*]
    → [outline: plan → review → approve/revise*]
    → [content: draft → persona enforce → review → approve/revise*]
    → [design: apply tokens → preview → review → approve/revise*]
    → [images: render → filmstrip review → approve/revise*]
    → [final_review: blog + caption + scores → review → approve/revise*]
    → approved_for_publish (still not public)
    → Publish panel: caption edits, Instagram/LinkedIn
    → POST /publish → is_public=true
    → /blog/{id} live for all users

* revise loops within phase via feedback → subagent regeneration
```

---

## 13. Documentation Updates

- [ADR-007: Consolidate Carousel Pipelines Under DeepAgents](../decisions/0007-consolidate-carousel-pipelines-under-deepagents.md) — records this decision including skills refactor (status: proposed).
- Update `docs/backend/carousel-pipeline-plan.md` status to superseded by this plan; note skills layout change.
- Update `docs/backend/AGENTIC_REFACTOR_PLAN.md` §9.1 to reflect `_shared/` + `phases/` structure.
- Update `backend/CLAUDE.md` AI orchestration section: legacy pipeline removed; standards live in `skills/carousel-pipeline/_shared/`.
- Add `skills/carousel-pipeline/_shared/README.md` documenting the three-layer alignment (skills → prompts → code).
- Gherkin scenarios: `backend/tests/features/carousel_pipeline_consolidation.feature`, `frontend/tests/features/carousel_editorial_consolidation.feature` (see §15).

---

## 14. Success Criteria

| Criterion | Measure |
|-----------|---------|
| Single pipeline | No code path calls `execute_pipeline` or legacy graph |
| All gates show artifacts | Every `awaiting_human` phase has non-empty review payload |
| Feedback drives revision | Revise action regenerates phase output using stored feedback |
| No stuck workflows | Approve and revise never leave graph at END while awaiting human |
| Resume latency | `/workflow/resume` returns in under 2 seconds (human input only) |
| Unified progress | No frontend reference to legacy stream endpoints |
| Blog visibility | `/blog/{id}` 404 for unpublished content regardless of role |
| Preview works | Editors preview draft blog/design in create workspace |
| Publish is explicit | `is_public` only via `/publish` |
| DeepAgents orchestration | Carousel workflow uses `create_deep_agent` with registered subagents |
| Langfuse complete | Traces span all phases with human review linkage |
| End-to-end | Create → publish → public blog works without manual intervention |
| Standards preserved | All monolith specs live in `skills/carousel-pipeline/_shared/`; no content lost from refactor |
| Progressive disclosure | Parent agents load no carousel skill; phase subagents load one phase + minimal `_shared/` |
| Prompt alignment | `agents/prompts/carousel/` matches `_shared/content-contracts` and `text-formatting` |
| Gherkin coverage | All §15 scenarios implemented and passing in CI |
| Task completion | All §16 tasks meet acceptance criteria |
| SSE transport | Status updates via SSE; polling only on SSE failure |
| CI quality gates | All §17 gates pass for touched backend/frontend paths |

---

## 15. Gherkin Scenarios

Gherkin-first per project standards (**CLAUDE.md**). Feature files are the **authoritative behavior spec**; automated tests must implement these scenarios—not parallel ad-hoc test plans.

### 15.0 Test implementation rules

| Rule | Requirement |
|------|-------------|
| **Source of truth** | Scenarios in §15.2 are written before or alongside implementation (SDD) |
| **Backend** | Each scenario maps to pytest tests with comment: `# Scenario: <exact Gherkin scenario name>` |
| **Frontend** | Each UI scenario maps to Vitest and/or Playwright with the same comment reference |
| **No orphan tests** | New tests for this refactor must trace to a Gherkin scenario; untraced tests fail review |
| **Tag filtering** | Use `@cp-consolidation` to run the consolidation suite in isolation |
| **CI** | Consolidation scenarios must pass in GitHub Actions before a stage (§11) is marked complete |

**Test type mapping:**

| Gherkin domain | Backend test location | Frontend test location |
|----------------|----------------------|------------------------|
| Workflow API, visibility, SSE API | `tests/integration/test_carousel_pipeline_consolidation.py` | — |
| Workflow engine units | `tests/unit/agents/`, `tests/unit/application/` | — |
| Create workspace UI, SSE client | — | `src/features/create/**/*.test.tsx`, Playwright E2E |
| E2E happy path | Integration (API) | Playwright (UI) |

### 15.1 Feature files

| File | Scope |
|------|-------|
| `backend/tests/features/carousel_pipeline_consolidation.feature` | API, workflow engine, streaming, visibility, legacy removal, skills, standards, recovery |
| `frontend/tests/features/carousel_editorial_consolidation.feature` | Create workspace UI, progress, preview vs public blog, legacy hook removal |

Existing files remain valid where not superseded: `phase3_workflow_collaboration.feature` (events/notifications), `rbac.feature` (public blog when `is_public=true`), `carousel_workflow.feature` (aspirational UX — consolidate overlapping scenarios into the files above during implementation).

### 15.2 Scenario index by domain

#### Workflow engine & resume (backend)

| Tag | Scenario | Type |
|-----|----------|------|
| @cp-happy-path | Start workflow and pause at first human gate | Happy |
| @cp-happy-path | Approve research advances to outline generation inside graph | Happy |
| @cp-edge @cp-revise | Revise research loops in-graph without stuck END checkpoint | Edge |
| @cp-edge @cp-revise | Revise after prior revise still accepts approve | Edge |
| @cp-edge @cp-feedback | Stored feedback is passed to regeneration on revise | Edge |
| @cp-edge @cp-revision-cap | Revision cap triggers escalation | Edge |
| @cp-edge @cp-lock | Optimistic lock conflict on concurrent resume | Edge |
| @cp-edge @cp-recovery | Resume workflow after server restart | Edge |

#### Phase artifacts (backend)

| Tag | Scenario | Type |
|-----|----------|------|
| @cp-happy-path | Content gate includes slide drafts and persona scores | Happy |
| @cp-edge @cp-persona | Content approve blocked when persona score below threshold | Edge |
| @cp-happy-path | Design gate includes design_applied and preview metadata | Happy |
| @cp-happy-path | Images gate includes image asset references | Happy |
| @cp-happy-path | Final review gate includes blog caption and rubric scores | Happy |
| @cp-edge @cp-final-review | Final review revise routes to selected earlier phase | Edge |

#### Progress streaming (backend + frontend)

| Tag | Scenario | Type |
|-----|----------|------|
| @cp-happy-path | Stream emits progress during in_progress phase | Happy |
| @cp-edge @cp-stream-idle | Stream does not emit legacy idle pending loops | Edge |
| @cp-happy-path | Phase progress persists on project row for reload | Happy |
| @cp-happy-path @cp-sse-primary | SSE delivers phase_change without polling during approve | Happy |
| @cp-happy-path @cp-sse-primary | Stream emits initial snapshot on connect | Happy |
| @cp-happy-path @cp-sse-primary | Live progress events arrive during long resume without state polling | Happy |
| @cp-happy-path @cp-sse-primary | Progress events include nested phase_progress payload | Happy |
| @cp-edge @cp-sse-primary | Multiple progress events increase monotonically during parallel image generation | Edge |
| @cp-edge @cp-sse-primary | Multiple SSE subscribers receive the same progress event | Edge |
| @cp-edge @cp-stream-idle | Stream sends keepalive without repeating progress at human gate | Edge |
| @cp-edge @cp-sse-primary | SSE stream stays open during resume longer than keepalive interval | Edge |
| @cp-happy-path @cp-sse-rate-limit | Rapid workflow state reads do not return 429 | Happy |
| @cp-edge @cp-sse-rate-limit | Fallback polling burst stays under rate limit after SSE disconnect | Edge |
| @cp-edge @cp-sse-auth | Unauthenticated workflow stream returns 401 | Edge |
| @cp-edge @cp-sse-auth | Editor without project access cannot subscribe to workflow stream | Edge |
| @cp-edge @cp-sse-auth | Unauthenticated workflow state returns 401 | Edge |
| @cp-edge @cp-sse-fallback | Polling fallback activates only when SSE disconnects | Edge |
| @cp-edge @cp-sse-fallback | Polling fallback stops when SSE reconnects | Edge |
| @cp-edge @cp-sse-fallback | Polling fallback does not run while SSE is healthy during loading | Edge |
| @cp-edge @cp-sse-fallback | Polling fallback stops at awaiting_human gate | Edge |
| @cp-happy-path | Progress strip active during in_progress only | Happy |
| @cp-edge @cp-stream-idle | No progress polling loop at awaiting_human gate | Edge |
| @cp-happy-path @cp-sse-primary | Mount hydrates workflow state once then opens SSE | Happy |
| @cp-happy-path @cp-sse-primary | Live SSE progress updates slide grid during approve without state polling | Happy |
| @cp-happy-path @cp-sse-primary | SSE progress merges nested phase_progress into client state | Happy |
| @cp-edge @cp-sse-primary | No loading-time workflow state poll while SSE is healthy | Edge |
| @cp-edge @cp-sse-fallback | Fallback polling does not receive 429 from workflow state | Edge |
| @cp-edge @cp-stream-idle | No workflow state poll loop after loading completes at human gate | Edge |
| @cp-happy-path | Reload restores persisted phase progress snapshot | Happy |

#### Blog visibility & publish (backend + frontend)

| Tag | Scenario | Type |
|-----|----------|------|
| @cp-happy-path | Anonymous user reads public blog when is_public is true | Happy |
| @cp-edge @cp-visibility-draft | Anonymous user cannot read draft blog on public media route | Edge |
| @cp-edge @cp-visibility-admin | Admin cannot read draft blog on public media route | Edge |
| @cp-happy-path | Editor previews draft blog via preview route | Happy |
| @cp-edge @cp-visibility-draft | Anonymous user cannot access preview route | Edge |
| @cp-happy-path | Final review approve does not set is_public | Happy |
| @cp-happy-path | Explicit publish sets is_public | Happy |
| @cp-edge @cp-visibility-admin | Admin sees 404 on public blog page for draft carousel | Edge |
| @cp-happy-path | Editor previews draft blog inside create workspace | Happy |
| @cp-happy-path | Public blog page has no admin publish panel | Happy |
| @cp-happy-path | Publish panel appears after final review approval | Happy |
| @cp-happy-path | Publish to site makes public blog accessible | Happy |

#### Legacy removal & RAG (backend + frontend)

| Tag | Scenario | Type |
|-----|----------|------|
| @cp-happy-path | Legacy generate endpoint returns 404 or 410 | Happy |
| @cp-happy-path | Legacy stream endpoint returns 404 or 410 | Happy |
| @cp-happy-path | Caption endpoint does not run full legacy pipeline | Happy |
| @cp-happy-path | Generate carousel tool starts workflow not legacy pipeline | Happy |
| @cp-happy-path | Create workspace does not reference legacy stream constants | Happy |

#### Skills & standards (backend)

| Tag | Scenario | Type |
|-----|----------|------|
| @cp-happy-path | Shared standards files exist after migration | Happy |
| @cp-happy-path | Monolithic workflow content is preserved in shared standards | Happy |
| @cp-edge @cp-skills | RAG parent agent does not load full carousel pipeline skill | Edge |
| @cp-happy-path | Generated slide content strips em dashes | Happy |
| @cp-edge @cp-standards | Invalid content JSON fails loudly without stub slide | Edge |
| @cp-happy-path | Closing slide uses structured checklist not prose wall | Happy |

#### Review UI (frontend)

| Tag | Scenario | Type |
|-----|----------|------|
| @cp-happy-path | Research gate shows findings and feedback composer | Happy |
| @cp-happy-path | Final review tab shows carousel blog caption and quality scores | Happy |
| @cp-edge @cp-ui-revise | Request revision requires feedback text | Edge |
| @cp-happy-path | Outline revise sends structured reorder payload | Happy |
| @cp-edge @cp-ui-persona | Content approve disabled when persona score below threshold | Edge |
| @cp-happy-path | Send final review back to content phase | Happy |

### 15.3 Edge-case coverage map (defects → scenarios)

| Known defect (§2) | Scenario(s) |
|-------------------|---------------|
| Reject routes to END / stuck gate | Revise research loops in-graph without stuck END checkpoint |
| Blocking resume | Approve research advances… response within 2 seconds |
| Empty artifacts at gates | Content/Design/Images/Final review gate scenarios |
| Infinite legacy stream loop | Stream idle + frontend no polling loop scenarios |
| Polling replaces SSE as primary | SSE delivers phase_change without polling; fallback only on disconnect |
| Feedback ignored | Stored feedback passed to regeneration on revise |
| Admin draft on public blog | Admin cannot read draft… + Admin sees 404 on public blog page |
| Auto is_public on approve | Final review approve does not set is_public |
| Legacy caption runs full pipeline | Caption endpoint does not run full legacy pipeline |

---

## 16. Development Tasks and Acceptance Criteria

Each task is complete only when **all** acceptance criteria pass, **linked Gherkin scenarios are green**, and **§17 CI quality gates pass** for all files touched by the task.

### 16.0 Global definition of done (every task)

Before marking any CP-* task complete:

- [ ] **Gherkin:** Linked scenarios from §15.2 implemented; tests include `# Scenario: …` comments
- [ ] **Backend CI** (if backend touched): ruff format + check, mypy strict, lint-imports, interrogate ≥80%, pytest green, diff-cover ≥75% on PR diff, mutmut on workflow modules, vulture clean
- [ ] **Frontend CI** (if frontend touched): ESLint, typecheck, Vitest green, Prettier check, Stryker on touched hooks/components
- [ ] **Architecture:** No magic strings; constants extracted; no `any`; files ≤400 lines; Clean Architecture import rules preserved
- [ ] **Security:** Input sanitized via `sanitize_llm_input` on feedback paths
- [ ] **Observability:** Langfuse handler on new LLM paths; workflow events on phase transitions

### Stage A — Skills refactor and engine core

#### CP-001: Migrate carousel skills to `_shared/` + `phases/`

**Gherkin:** Shared standards files exist after migration; Monolithic workflow content is preserved in shared standards

**Acceptance criteria:**

- [ ] `skills/carousel-pipeline/_shared/` contains all seven standard files listed in §3.4
- [ ] `skills/carousel-pipeline/phases/` contains research, outline, content, design, images, final-review skills
- [ ] Top-level `SKILL.md` is slim (routing only, no full workflow dump)
- [ ] `workflow.md` deprecated with pointer to new layout; no content lost (diff review against monolith)
- [ ] `skills/carousel-pipeline/_shared/README.md` documents three-layer alignment

#### CP-002: Align runtime prompts with shared standards

**Gherkin:** Generated slide content strips em dashes; Closing slide uses structured checklist not prose wall

**Acceptance criteria:**

- [ ] `agents/prompts/carousel/v1/` templates reference content-contracts and text-formatting rules
- [ ] Content agent output validated against slide-type shapes in code
- [ ] Renderer strips em dashes defensively per `_shared/text-formatting.md`

#### CP-003: Graph retry loops (no END on revise)

**Gherkin:** Revise research loops in-graph without stuck END checkpoint; Revise after prior revise still accepts approve

**Acceptance criteria:**

- [ ] All phase conditional edges route `_ROUTE_RETRY` to same phase node, not `END`
- [ ] `phase_feedback` and `revision_count` updated on revise
- [ ] `_needs_gate_reopen` workaround removed or reduced to migration-only path

#### CP-004: Move generation into phase nodes

**Gherkin:** Approve research advances to outline…; Content gate includes slide drafts…

**Acceptance criteria:**

- [ ] `_prepare_phase_before_resume` removed or reduced to no AI calls
- [ ] Outline generated on outline phase enter, not on research approve in service layer
- [ ] Content, design, images artifacts exist before `awaiting_human` interrupt
- [ ] `POST /workflow/resume` p95 latency under 2 seconds (human input only)

#### CP-005: CarouselEditorialOrchestrator + phase subagents

**Gherkin:** Start workflow and pause at first human gate; Stored feedback passed to regeneration

**Acceptance criteria:**

- [ ] Deep Agent orchestrator wraps revised LangGraph with checkpointer per `project_id`
- [ ] Phase subagents registered: research_synthesizer, outline_planner, content_drafter, caption_writer
- [ ] Each subagent loads scoped skills per §3.4 progressive disclosure table
- [ ] Deterministic nodes wired: apply_design, render_images, compose_blog, score_quality, sync_slides

#### CP-006: Unified workflow SSE

**Gherkin:** Stream emits progress during in_progress; Stream does not emit legacy idle pending loops; Phase progress persists; SSE delivers phase_change without polling during approve

**Acceptance criteria:**

- [ ] `/workflow/stream` emits phase_change, progress, artifact, review_required, error events per §5.1
- [ ] `phase_progress` JSONB updated from nodes during generation
- [ ] No backend code writes legacy stream idle `pending` for editorial projects
- [ ] Stream emits `review_required` and post-resume `phase_change` so frontend does not depend on poll to clear `loading`
- [ ] Integration test: `# Scenario: SSE delivers phase_change without polling during approve`

#### CP-006b: Frontend SSE-primary transport with polling fallback

**Gherkin:** Polling fallback activates only when SSE disconnects; Polling fallback stops when SSE reconnects; No progress polling loop at awaiting_human gate

**Acceptance criteria:**

- [ ] `useEditorialWorkflow` removes unconditional 3s poll during `loading`
- [ ] Single `GET /workflow/state` on mount; ongoing updates via SSE event handlers
- [ ] Fallback poll starts only on SSE `error`/`onerror`; exponential backoff; stops on reconnect
- [ ] No interval poll when `phase_status === awaiting_human`
- [ ] `EditorialWorkflowProgress` does not open second EventSource; consumes shared hook state
- [ ] Vitest tests with `# Scenario: Polling fallback activates only when SSE disconnects`
- [ ] Vitest tests with `# Scenario: Polling fallback stops when SSE reconnects`

#### CP-007: Feedback learning persistence

**Gherkin:** Stored feedback is passed to regeneration on revise

**Acceptance criteria:**

- [ ] Corrections stored in Postgres (not in-memory dict)
- [ ] `get_relevant_examples()` queried on revise before subagent regeneration
- [ ] Structured user edits recorded as corrections when differing from AI output

#### CP-008: Persona gate on content approve

**Gherkin:** Content approve blocked when persona score below threshold; Content approve disabled when persona score below threshold (UI)

**Acceptance criteria:**

- [ ] `PersonaAgent.enforce()` runs before content review interrupt
- [ ] API returns 422 on approve when voice match below configured threshold
- [ ] Interrupt payload includes scores and forbidden phrase warnings

#### CP-009: Revision cap and optimistic locking

**Gherkin:** Revision cap triggers escalation; Optimistic lock conflict on concurrent resume

**Acceptance criteria:**

- [ ] `expected_version` on resume request; 409 on mismatch
- [ ] Default revision cap 5 per phase with admin notification on exceed
- [ ] Audit log records feedback excerpt on review events

#### CP-010: RAG parent skill scoping

**Gherkin:** RAG parent agent does not load full carousel pipeline skill

**Acceptance criteria:**

- [ ] `skills=["skills/carousel-pipeline"]` removed from parent `RAGAgent`
- [ ] Phase skills attached to subagent runnables only
- [ ] `bmad-skill-manifest.yaml` updated for editorial workflow

### Stage B — Visibility and preview

#### CP-011: Preview API routes

**Gherkin:** Editor previews draft blog via preview route; Anonymous user cannot access preview route

**Acceptance criteria:**

- [ ] `GET /preview/blog/{lang}`, `/preview/design/{lang}`, `/preview/images/{slide}` implemented
- [ ] `assert_carousel_project_access` guard on all preview routes
- [ ] Responses use `Cache-Control: private, no-store`

#### CP-012: Public media guards tightened

**Gherkin:** Anonymous/Admin cannot read draft on public media route

**Acceptance criteria:**

- [ ] `assert_carousel_public_or_editor` replaced with `assert_carousel_public` on public blog/design/image routes
- [ ] No bypass for `current_phase == published` without `is_public=true`

#### CP-013: Publish separation

**Gherkin:** Final review approve does not set is_public; Explicit publish sets is_public

**Acceptance criteria:**

- [ ] `_sync_project_phase` does not set `is_public`
- [ ] Final approve sets `workflow_status: approved_for_publish` only
- [ ] `POST /publish` sets `is_public=true` and `current_phase=published`

#### CP-014: Public blog page draft 404

**Gherkin:** Admin sees 404 on public blog page for draft carousel

**Acceptance criteria:**

- [ ] `/blog/[id]` returns notFound when project `is_public=false` regardless of session role
- [ ] `fetchBlogWithDesign` does not use editor bypass on public fetch path

#### CP-015: Admin panel relocation

**Gherkin:** Public blog page has no admin publish panel

**Acceptance criteria:**

- [ ] `BlogPostAdminPanel` removed from public blog page
- [ ] Publish/delete/edit actions available in create workspace final review and publish panel only

### Stage C — Review UI and feedback

#### CP-016: Phase review shell

**Gherkin:** Research gate shows findings and feedback composer; Final review tab shows carousel blog caption and quality scores

**Acceptance criteria:**

- [ ] Every gate renders artifact viewer + feedback composer + Approve + Request revision
- [ ] `EditorialPhaseReview` implements all phases including `final_review` tabs
- [ ] i18n strings for all new UI labels (en + pt)

#### CP-017: Revise flow and validation

**Gherkin:** Request revision requires feedback text; Outline revise sends structured reorder payload

**Acceptance criteria:**

- [ ] Revise blocked client-side and server-side when feedback empty
- [ ] `structured_feedback` sent for outline reorder, slide edits, final-review send-back target
- [ ] Hardcoded `"Needs revision"` reject string removed

#### CP-018: Unified progress UI

**Gherkin:** Progress strip active during in_progress only; No progress polling loop at awaiting_human gate; SSE delivers phase_change without polling during approve

**Acceptance criteria:**

- [ ] `EditorialWorkflowProgress` uses hook SSE state only (no direct legacy stream)
- [ ] `useCarouselStream` / `useCarouselStatus` not imported in create workspace
- [ ] Progress component enabled only when `phase_status === in_progress`
- [ ] Approve/resume flow clears loading via SSE `phase_change`, not poll
- [ ] §17 frontend CI gates pass for edited components

#### CP-019: Final review send-back

**Gherkin:** Final review revise routes to selected earlier phase; Send final review back to content phase

**Acceptance criteria:**

- [ ] UI phase picker on final review revise (research, outline, content, design, images)
- [ ] Backend honors `structured_feedback.target_phase`

#### CP-020: Persona threshold UI

**Gherkin:** Content approve disabled when persona score below threshold

**Acceptance criteria:**

- [ ] Approve button disabled with explanatory copy when score below threshold
- [ ] Persona badge visible per slide in content review

#### CP-021: Workspace draft blog preview

**Gherkin:** Editor previews draft blog inside create workspace

**Acceptance criteria:**

- [ ] Final review Blog tab loads `/preview/blog/{lang}` not public blog URL
- [ ] Carousel preview embedded in final review Carousel tab

#### CP-022: Publish panel gating

**Gherkin:** Publish panel appears after final review approval; Publish to site makes public blog accessible

**Acceptance criteria:**

- [ ] Publish panel accessible only when `workflow_status === approved_for_publish`
- [ ] Explicit publish action calls `POST /publish`
- [ ] Success navigates to confirmation with link to live public blog

### Stage D — Legacy removal and RAG

#### CP-023: Delete legacy API routes

**Gherkin:** Legacy generate/stream endpoints return 404 or 410

**Acceptance criteria:**

- [ ] `generation.py` routes removed from router
- [ ] No references to `execute_pipeline` / `stream_pipeline` in route handlers
- [ ] Integration tests updated; legacy route tests removed or inverted

#### CP-024: Remove legacy backend modules

**Acceptance criteria:**

- [ ] `carousel_orchestrator/`, `graph.py` (monolith), full-pipeline `subagent.py` deleted
- [ ] `CarouselAgent` protocol removed; DI updated
- [ ] Deterministic helpers inlined via graph nodes (same functions, new call path)

#### CP-025: Caption and publish route rewrite

**Gherkin:** Caption endpoint does not run full legacy pipeline

**Acceptance criteria:**

- [ ] `POST /caption` reads from workflow state or invokes caption_writer only
- [ ] No `execute_pipeline` in publishing routes

#### CP-026: RAG generate_carousel tool

**Gherkin:** Generate carousel tool starts workflow not legacy pipeline

**Acceptance criteria:**

- [ ] Tool calls `POST /workflow/start` (or service equivalent)
- [ ] Carousel editorial subagent on RAG uses unified orchestrator checkpointer

#### CP-027: Frontend legacy hook removal

**Gherkin:** Create workspace does not reference legacy stream constants

**Acceptance criteria:**

- [ ] `CAROUSEL_GENERATE`, `CAROUSEL_STREAM`, `CAROUSEL_STATUS`, `CAROUSEL_RESUME` removed from `constants/api.ts`
- [ ] `use-carousel.ts` stream/status/generate hooks deleted
- [ ] Related unit tests deleted or rewritten

#### CP-028: Content standards fail-loud

**Gherkin:** Invalid content JSON fails loudly without stub slide

**Acceptance criteria:**

- [ ] Unparseable content agent JSON raises workflow error event
- [ ] Project not marked completed with stub single-slide fallback

### Stage E — Verification and documentation

#### CP-029: Full Gherkin suite green

**Gherkin:** All scenarios in §15.2

**Acceptance criteria:**

- [ ] `backend/tests/integration/test_carousel_pipeline_consolidation.py` implements all backend feature scenarios
- [ ] Frontend Vitest + Playwright cover all `carousel_editorial_consolidation.feature` scenarios
- [ ] Every test method/name documents matching Gherkin scenario in comment or docstring
- [ ] `uv run pytest tests/integration/test_carousel_pipeline_consolidation.py -v` green in CI
- [ ] No consolidation test added without a Gherkin scenario reference (review checklist item)
- [ ] §17 CI workflows green on the consolidation PR branch

#### CP-030: Langfuse and workflow board

**Acceptance criteria:**

- [ ] Traces grouped by `project_id` span all phases with human review metadata
- [ ] Workflow board columns reflect unified `workflow_status` and phase fields
- [ ] Notifications deep-link to create workspace with phase query param

#### CP-031: Documentation and ADR acceptance

**Acceptance criteria:**

- [ ] ADR-007 status moved to Accepted after Stage E
- [ ] `docs/backend/carousel-pipeline-plan.md` marked superseded
- [ ] `docs/backend/AGENTIC_REFACTOR_PLAN.md` §9.1 updated

### 16.1 Traceability matrix (task → scenario)

| Task | Primary Gherkin scenarios |
|------|---------------------------|
| CP-001 | Shared standards files exist; Monolithic content preserved |
| CP-002 | Em dashes stripped; Closing checklist structure |
| CP-003 | Revise loops in-graph; Revise then approve |
| CP-004 | Approve research → outline; Resume under 2s; Artifact gates |
| CP-005 | Start workflow; Feedback regeneration |
| CP-006 | Stream progress; No idle loop; Persisted phase_progress; SSE without poll on approve; Live progress during resume; Nested phase_progress payload; Initial SSE snapshot |
| CP-006b | SSE fallback activate/stop; No poll at awaiting_human; No loading poll while SSE healthy; No 429 on state reads; SSE auth edge cases |
| CP-007 | Stored feedback regeneration |
| CP-008 | Persona threshold API + UI |
| CP-009 | Revision cap; Optimistic lock |
| CP-010 | RAG parent skill scoping |
| CP-011 | Preview route happy + 401 |
| CP-012 | Draft 404 on public media |
| CP-013 | Approve without is_public; Explicit publish |
| CP-014 | Admin 404 public blog draft |
| CP-015 | No admin panel on public blog |
| CP-016 | Research + final review UI |
| CP-017 | Feedback required; Outline reorder |
| CP-018 | Progress in_progress only; No stream polling; SSE on approve |
| CP-019 | Final review send-back |
| CP-020 | Content approve disabled |
| CP-021 | Workspace blog preview |
| CP-022 | Publish panel gating |
| CP-023 | Legacy endpoints 404/410 |
| CP-024 | (No legacy modules — verified by grep + build) |
| CP-025 | Caption without full pipeline |
| CP-026 | RAG tool starts workflow |
| CP-027 | No legacy frontend constants |
| CP-028 | Invalid JSON fail loud |
| CP-029 | All §15 scenarios green + §17 CI |
| CP-030 | (Observability — extend phase3 board/notifications scenarios) |
| CP-031 | Docs updated |

---

## 17. CI Quality Gates (must pass per task)

All consolidation work must keep **GitHub Actions quality gates** green. Tasks in §16 inherit these via §16.0.

### 17.1 Backend (`.github/workflows/backend-quality-gates.yml`)

| Gate | Command / threshold | Applies to |
|------|---------------------|------------|
| Format | `uv run ruff format --check src/` | All touched Python |
| Lint | `uv run ruff check src/` | All touched Python |
| Types | `uv run mypy rag_backend/ --explicit-package-bases` | All touched Python |
| Architecture | `uv run lint-imports` | New modules; layer boundaries |
| Docstrings | `uv run interrogate src/` ≥ **80%** | Touched packages |
| Security | Bandit + pip-audit | All touched Python |
| Tests | `uv run pytest` green | All tests |
| Diff coverage | `diff-cover --fail-under=75` vs `origin/main` | Every PR |
| Mutation | `uv run mutmut run` | Workflow service, agents, graph nodes |
| Dead code | `uv run vulture src/ --min-confidence 80` | Legacy removal verification |

**Project targets (CLAUDE.md):** 90%+ branch coverage on new business logic; mutmut ≥ **70%** on consolidation modules (establish baseline on first green run, enforce on subsequent PRs).

**Consolidation mutation scope (minimum):**

- Orchestrator + `carousel_workflow.py` (or successor)
- `editorial_workflow_service.py`
- Phase subagent registry
- SSE stream handler / workflow route changes

### 17.2 Frontend (`.github/workflows/frontend-quality-gates.yml`)

| Gate | Command | Applies to |
|------|---------|------------|
| Lint | `npm run lint` | Touched TS/TSX |
| Types | `npm run typecheck` | Touched TS/TSX |
| Unit tests | `npm run test -- --run` | New/changed hooks and components |
| Mutation | `npm run test:mutate` (Stryker) | `use-editorial-workflow.ts`, progress/review components |
| Format | Prettier check | Touched files |

**Project target:** Stryker ≥ **70%** on touched hooks/components (ADR-005).

### 17.3 Gherkin ↔ CI workflow

1. Add or update scenario in `.feature` file (§15).
2. Implement pytest / Vitest / Playwright with `# Scenario: …` comment.
3. Run §17.1 and §17.2 commands locally on touched paths.
4. Open PR; both GitHub workflows must be green.
5. Mark CP-* task done only when scenario tests + gates pass.

**Recommended local checks (consolidation PRs):**

```bash
cd backend && uv run ruff check src/ && cd src && uv run mypy rag_backend/ --explicit-package-bases && cd .. && uv run pytest tests/integration/test_carousel_pipeline_consolidation.py -v
cd frontend && npm run typecheck && npm run test -- --run src/features/create/
```

### 17.4 Architecture checklist (code review)

- [ ] No magic strings; SSE event names and workflow actions in constants
- [ ] No `any` in new public APIs
- [ ] Max 400 lines per file; split if exceeded
- [ ] ADR-007: SSE primary, polling fallback only, visibility model, Deep Agents orchestration
- [ ] Stage D: no remaining legacy endpoint constants or hooks (grep verification)

---
