# ADR-007: Consolidate Carousel Pipelines Under DeepAgents Editorial Orchestrator

## Status

Accepted

## Context

Alter-Ego currently operates **two carousel generation pipelines** in parallel:

| Pipeline | API | Orchestration |
|----------|-----|---------------|
| Editorial workflow | `/api/carousels/{id}/workflow/*` | Raw LangGraph (`CarouselWorkflowEngine`) with `interrupt()` gates |
| Legacy generation | `/api/carousels/{id}/generate`, `/stream`, `/status`, `/resume` | `CarouselAgent` → monolithic `build_graph()` pipeline |

The create workspace bridges both: editorial workflow handles human gates while the frontend polls the legacy stream for design and image progress. This dual architecture causes production defects:

- Workflows stuck at `awaiting_human` after reject (graph routes retry to `END`)
- Blocking `POST /workflow/resume` (heavy generation runs before graph resume)
- Empty review panels at content and design gates
- Infinite legacy `/stream` polling when editorial workflow is idle
- Reviewer feedback recorded but not used for regeneration
- Draft carousel blog visible to admins on public `/blog/{id}` routes via `assert_carousel_public_or_editor`
- Automatic `is_public=true` on workflow completion, conflating editorial approval with public release

ADR-002 established LangGraph as the workflow engine. ADR-003 requires persona enforcement and feedback learning. ADR-004 requires event-driven phase transitions. The pivot plan (`docs/plans/carousel-pipeline-consolidation.md`) specifies the target design. This ADR records the architectural decision to execute that consolidation.

## Decision Drivers

- Single source of truth for carousel AI orchestration — no duplicate graphs or API surfaces
- Every workflow phase must render review artifacts and accept feedback that drives revision
- Human approval gates must not block HTTP responses for minutes (generation belongs in graph nodes)
- Progress streaming must come from the same pipeline that owns state transitions
- Unpublished content must never appear on public blog routes, regardless of user role
- Public release must be an explicit action separate from final editorial approval
- Align with project AI orchestration standards: Deep Agents for complex workflows, raw LangGraph for deterministic nodes (see `docs/architecture/langchain-deep-agents-guide.md`)
- Preserve existing agent modules (`SourceSynthesisAgent`, `OutlineAgent`, `ContentDraftAgent`, `PersonaAgent`, `QualityAgent`) — wrap, do not rewrite
- Preserve carousel content standards from `skills/carousel-pipeline/` (return types, slide contracts, design tokens, typography, image rules, text formatting, anti-patterns) via progressive disclosure — not by loading the full monolithic skill on every agent init

## Decision

Consolidate all carousel AI work into a **single editorial pipeline** orchestrated by a **Deep Agent** (`CarouselEditorialOrchestrator`), with the following properties:

### 1. One API surface

All carousel generation flows through `/api/carousels/{id}/workflow/*`:

- `POST /workflow/start` — begin workflow
- `GET /workflow/state` — current state and artifacts
- `POST /workflow/resume` — human approve or revise with feedback
- `GET /workflow/stream` — unified SSE for phase changes, granular progress, and review-required events

**Remove** legacy endpoints: `/generate`, `/stream`, `/status`, `/resume`.

Workspace-only preview routes (`/preview/blog`, `/preview/design`, `/preview/images`) serve authenticated editors; public media routes require `is_public=true` for all callers.

### 2. DeepAgents orchestration model

| Layer | Abstraction | Responsibility |
|-------|-------------|----------------|
| Orchestrator | `create_deep_agent` (`CarouselEditorialOrchestrator`) | Seven-phase state machine, planning todos, `interrupt()` gates, subagent spawning |
| Phase subagents | `CompiledSubAgent` registrations | Research synthesis, outline planning, content drafting, caption writing — each wraps an existing agent module |
| Deterministic nodes | Raw LangGraph async functions | Design tokens, image rendering, PDF export, blog composition, quality scoring, slide DB sync |

The orchestrator uses one checkpointer thread per `project_id`. Subagents receive structured input including prior artifacts and reviewer feedback; output merges into `CarouselWorkflowState`.

Persona enforcement (`PersonaAgent.enforce()`) runs as a deterministic gate after content drafting, before the content review interrupt — not as a separate Deep Agent.

RAG integration: the `generate_carousel` tool starts the editorial workflow instead of invoking the legacy pipeline. The orchestrator registers as a `CompiledSubAgent` on `RAGAgent` only (`AlterEgoAgent` remains carousel-free).

All LLM invocations trace through Langfuse with `project_id`, `phase`, `agent_name`, and `user_id` metadata.

### 7. Skills, standards, and progressive disclosure

**Skills are not subagents.** Deep Agents `skills/` paths load markdown instructions into an LLM context stack. `CompiledSubAgent` entries require executable runnables (LangGraph graphs wrapping Python agents). The legacy mistake was attaching the entire `skills/carousel-pipeline` monolith to `RAGAgent` while also registering a full-pipeline subagent — duplicating context and defeating progressive disclosure.

**Preserve standards; refactor structure.** The existing `skills/carousel-pipeline/SKILL.md` and `workflow.md` contain essential, battle-tested specifications that must not be discarded:

| Category | Examples preserved |
|----------|-------------------|
| **Return types** | Content JSON shape (`slides`, `blog_pt`, `blog_en`, titles/subtitles); design token schema; `ResearchSource` fields |
| **Slide contracts** | Per-type body shapes (`intro`, `content`, `closing` checklist, `cta`); `features`, `stats`, `insight` structured extras |
| **Text formatting** | pt-BR/en tone rules; em-dash ban; `**bold**` vs `` `code` `` emphasis; heading accent highlights (max 2 words) |
| **Design system** | Theme palettes and brand detection; typography sizes for 1080×1350; `.feature-grid`, intro footer flex layout |
| **Image generation** | Scene-description-only `image_prompt`; server-side Gemini wrapper template; intro + content slides only |
| **Export & caption** | 1080×1350 JPEG export; caption structure (hook, CTA, 12–18 hashtags) |
| **Anti-patterns** | Symptom/root-cause/fix table from production failures |
| **Operational rules** | User sources authoritative; fail loudly on JSON parse; bilingual storage in `blog_translations` |

**Target skills layout** (refactor, not delete):

```
skills/carousel-pipeline/
├── SKILL.md                 # Slim entry: purpose, triggers, phase routing (no full workflow dump)
├── bmad-skill-manifest.yaml # Updated manifest
├── _shared/                 # Canonical standards extracted from current monolith
│   ├── critical-rules.md
│   ├── anti-patterns.md
│   ├── content-contracts.md
│   ├── text-formatting.md
│   ├── design-system.md
│   ├── image-generation.md
│   └── export-and-caption.md
└── phases/                  # Phase-scoped skills for progressive disclosure
    ├── research/SKILL.md
    ├── outline/SKILL.md
    ├── content/SKILL.md
    ├── design/SKILL.md
    ├── images/SKILL.md
    └── final-review/SKILL.md
```

`skills/carousel-refinement/` remains for copy/design/image refinement (maps to refinement tools).

**Three-layer alignment** (single standards, multiple consumers):

| Layer | Role | Alignment rule |
|-------|------|----------------|
| `skills/carousel-pipeline/_shared/` | Human-readable canonical standards | Source of truth for behavior specs |
| `agents/prompts/carousel/` | Runtime Jinja2/YAML templates | Must reflect `_shared/` contracts; document mapping in each phase folder README |
| Python agents + renderers | Execution and validation | Enforce contracts in code (JSON schema, em-dash strip, slide dimensions, token shapes) |

**Progressive disclosure rules:**

- **Parent agents** (`RAGAgent`): remove `skills=["skills/carousel-pipeline"]` from `create_deep_agent`. Parent loads only its RAG system prompt; carousel work delegates via `task` to subagents.
- **Phase subagents**: each `CompiledSubAgent` loads **one phase skill** plus **only the `_shared/` files relevant to that phase** (e.g., content subagent loads `phases/content` + `content-contracts`, `text-formatting`, `anti-patterns` subset).
- **Editorial orchestrator (API path)**: graph nodes invoke Python agents; phase skills are referenced when constructing subagent runnables or prompt context for that phase — not the full monolith at workflow start.
- **`workflow.md`**: deprecated after content migrates to `_shared/` + `phases/`; retain git history, replace file with pointer to new layout.

Skills instruct **what** good output looks like; Python agents **produce** it; prompts **parameterize** LLM calls. None replaces the others.

### 3. Uniform phase lifecycle

Every phase follows: **enter → generate → review interrupt → approve or revise**.

- **Approve** advances to the next phase; generation for the next phase runs on phase entry, not in the resume handler.
- **Revise** stores feedback in workflow state, increments revision count, and loops to regeneration within the same phase node — retry edges must not route to `END`.
- Resume handler persists human input and resumes the graph only; it does not run AI generation synchronously.

### 4. Per-phase human review and feedback

Each `interrupt()` payload includes all artifacts required for UI review. The create workspace renders phase-specific viewers and accepts:

- Free-text feedback (sanitized)
- Structured edits where applicable (slide text, outline order, send-back target on final review)

On revise, feedback is injected into the relevant subagent prompt and supplemented by persisted corrections from `FeedbackLearningLoop` (upgraded from in-memory to database storage).

Final review presents the bundled artifact set: carousel preview, blog markdown (both locales), caption, LinkedIn snippets, and rubric scores. Approval sets `approved_for_publish`; it does not set `is_public`.

### 5. Blog visibility and publish separation

| Surface | Access rule |
|---------|-------------|
| `/blog/{id}` (public layout) | `is_public=true` only — all roles, including admin |
| `/create/{id}/preview/*` | Authenticated project access only |
| Public media/blog/design/image API routes | `assert_carousel_public` — no editor bypass |
| `POST /carousels/{id}/publish` | Explicit public release; sets `is_public=true` |

Remove `assert_carousel_public_or_editor` from public routes. Remove automatic `is_public` assignment from workflow phase sync. Relocate admin controls from public blog pages to the create workspace and publish panel.

### 6. Legacy removal

Delete or replace:

- `api/routes/carousels/generation.py` and router registration
- `agents/carousel_orchestrator/` (full-pipeline orchestrator)
- `application/services/carousel/graph.py` (`build_graph` monolith)
- `CarouselAgent` protocol and `execute_pipeline` / `stream_pipeline`
- `application/services/carousel/subagent.py` full-pipeline wrapper — replace with per-phase subagent registry
- Frontend hooks and constants for legacy stream/status/generate
- Bridge pattern in `editorial_visual_pipeline.py` — deterministic helpers move into graph nodes under the unified orchestrator

**Keep and refactor** (not delete):

- `skills/carousel-pipeline/` — split into `_shared/` + `phases/`; preserve all standards listed in §7
- `skills/carousel-refinement/` — keep aligned with refinement tools

Caption generation rewrites to read from workflow state or invoke the caption subagent only — never the full pipeline.

## Considered Options

### Option 1: Keep dual pipelines; fix bugs independently

- **Good:** Smaller incremental changes; lower short-term risk
- **Bad:** Perpetuates architectural debt; frontend must forever bridge two state models; duplicate progress, checkpoint, and Langfuse tracing; defects recur at integration boundaries
- **Verdict:** Rejected — treats symptoms, not cause

### Option 2: Extend legacy pipeline with interrupts

- **Good:** Reuses rich `phase_progress` streaming already built into `CarouselAgent`
- **Bad:** Legacy graph is monolithic; retrofitting seven editorial gates and feedback loops into a pipeline designed for autonomous generation is harder than promoting the editorial workflow; contradicts pivot toward human-in-the-loop first
- **Verdict:** Rejected — wrong foundation

### Option 3: Keep raw LangGraph editorial engine; drop legacy only

- **Good:** Builds on existing `CarouselWorkflowEngine`; removes dual API surface
- **Bad:** Does not adopt DeepAgents subagent pattern recommended in project standards; orchestration logic in `EditorialWorkflowService` grows (generation in service layer caused current resume blocking bug); weaker isolation for parallel research and per-slide drafting
- **Verdict:** Rejected — solves API duplication but not orchestration quality

### Option 4: Unified DeepAgents editorial orchestrator (chosen)

- **Good:**
  - Single pipeline, single API, single SSE stream
  - DeepAgents planning and subagent spawning for research and content phases
  - Raw LangGraph nodes for deterministic work (design, images, export) — best of both abstractions per project guide
  - Feedback-driven revision loops inside the graph
  - Strict blog visibility model
  - Existing agent modules reused via CompiledSubAgent wrappers
  - Carousel standards preserved in refactored phase skills with progressive disclosure
- **Bad:**
  - Large refactor touching backend routes, graph topology, frontend create workspace, and RAG tools
  - Team must internalize DeepAgents + LangGraph hybrid pattern
  - Migration period requires careful sequencing to avoid breaking in-flight projects
- **Verdict:** Accepted

## Consequences

**Good:**

- Eliminates dual-pipeline integration bugs (stuck gates, infinite stream loop, empty review panels)
- Resume endpoint returns quickly; generation runs asynchronously inside graph nodes with progress streamed via unified SSE
- Reviewer feedback drives regeneration through subagent prompts and persisted learning loop
- Public blog surface is trustworthy — drafts never leak via admin session on `/blog/{id}`
- Publish is a deliberate, auditable action separate from editorial sign-off
- Aligns carousel orchestration with ADR-002 (LangGraph checkpoints), ADR-003 (persona + feedback), ADR-004 (workflow events), and the Deep Agents implementation guide
- Legacy code deletion reduces maintenance surface and test duplication
- Carousel quality standards remain documented in one place (`skills/carousel-pipeline/_shared/`) and enforced in code

**Bad:**

- Skills refactor requires keeping `_shared/` and `agents/prompts/` in sync when standards change
- In-flight carousel projects mid-legacy-pipeline need migration or restart policy at cutover
- DeepAgents API is beta; pin versions and review release notes (same discipline as ADR-002 for LangGraph)
- Unified SSE event schema becomes a contract both backend and frontend must version carefully

## Implementation Notes

Detailed sequencing, API extensions, state schema additions, frontend component changes, **Gherkin scenarios (§15)**, **tasks with acceptance criteria (§16)**, **SSE-primary transport**, and **CI quality gates (§17)** are specified in [Carousel Pipeline Consolidation Plan](../plans/carousel-pipeline-consolidation.md).

Key invariants during implementation:

- Never wrap `interrupt()` in bare `try/except` — re-raise `GraphInterrupt`
- Use `DeltaChannel` for append-only state fields to prevent checkpoint bloat
- Side effects before `interrupt()` must be idempotent
- `phase_progress` JSONB on `carousel_projects` mirrors SSE progress for page reload resilience
- Optimistic locking on resume prevents concurrent reviewer conflicts
- When changing carousel standards, update `skills/carousel-pipeline/_shared/` first, then align `agents/prompts/carousel/` and Python validators

## Supersedes / Amends

- **Amends ADR-002:** Carousel workflow orchestration adds a Deep Agents layer on top of LangGraph; checkpointing and `interrupt()` semantics unchanged
- **Implements ADR-003 feedback loop:** Persists corrections and feeds them into subagent regeneration
- **Implements ADR-004 events:** Phase transitions and review events emit through existing Redis Streams / workflow audit infrastructure

Does not supersede ADR-002 entirely — blog post editorial workflow and other LangGraph graphs remain governed by ADR-002.

## Related Decisions

- [ADR-002: Use LangGraph for Workflow Engine](0002-use-langgraph-for-workflow-engine.md)
- [ADR-003: Implement Persona-Driven AI Content Generation](0003-implement-persona-driven-ai-content.md)
- [ADR-004: Adopt Event-Driven Architecture for Content Workflows](0004-adopt-event-driven-architecture.md)
- [Carousel Pipeline Consolidation Plan](../plans/carousel-pipeline-consolidation.md)
- [LangChain Deep Agents Implementation Guide](../architecture/langchain-deep-agents-guide.md)

## Tags

#architecture #ai #workflow #carousel #deep-agents #langgraph #hitl #visibility #skills
