# Agent Architecture Restructure — Research + Plan (Architect)

**Mode:** architect / research+plan (read-only on production code)
**Author:** Architect skill
**Date:** 2026-06-18
**Repo:** alter-ego
**Scope:** prompt consolidation, runtime-skills relocation, `AGENTS.md` semantics, subagent taxonomy, a reusable Deep Agents harness (memory/middleware/checkpointer/store), the improvement loop, a runtime QA subagent, and a per-agent modular package layout — reconciled with Clean Architecture (ADR-009) and the DeepAgents consolidation (ADR-007).

> Dependency facts (pinned): `deepagents >= 0.5.3`, `langgraph == 1.2.5` (`backend/uv.lock`). DeepAgents `create_deep_agent` supports kwargs `model, tools, system_prompt, subagents, middleware, checkpointer, store, interrupt_on, permissions, memory` (memory = auto-loaded `AGENTS.md` files). Sources cited at the bottom.

---

## 0. Executive verdicts (jump table)

| Concern | Verdict |
|---|---|
| 1. Hardcoded prompts | **5 true violations** (worst: `agents/constants.py:39` `TEMPLATE_ENFORCE`, 41 lines). `quality_agent.py` is 100% off-registry. |
| 2. skills/ root org | `carousel-pipeline`, `carousel-refinement`, `knowledge-base` are **ALL STILL USED** at runtime. `runtime` standalone skill **does not exist** (container dir only). They *do* belong in the repo but should be cleanly fenced from delivery skills. |
| 3. `agents/AGENTS.md` | A persona/identity doc that **is NOT loaded by any code** (`grep` → 0 hits). It is a *latent* DeepAgents `memory=` file, not a wired system prompt. |
| 4. Subagent delegation | Two parallel mechanisms today; the DeepAgents `task`/subagent path is **half-wired** (specs carry `skills` but no `tools`/`runnable`/`model`). |
| 5. Harness | **No shared harness.** Checkpointer is centralized in `bootstrap/app_factory.py` but only the carousel engine consumes it; both Deep Agents run with **no checkpointer/store/middleware**. |
| 6. Improvement loop | Delivery-side loop exists (`/handoff` → `learnings-log.jsonl` → `/kaizen-skill session`). **No runtime/product equivalent.** |
| 7. Runtime QA | Does not exist. Playwright is present but only for **export geometry**, not QA of generated artifacts. |
| 8. Target structure | Per-agent packages are feasible *inside* `application/` but **conflict with Clean Architecture** if they hold infra; resolve via a thin agent-composition layer + the harness. |

---

## 1. Prompt organization — current state & target

### 1.1 Current state (evidence)

**Standard** (`registry.py`): prompts live under `agents/prompts/{domain}/{version}/` as `.md` (system) or `.yaml` (Jinja2 + model cfg); loaded via `get_system_prompt()` / `render_prompt()` (`backend/src/rag_backend/agents/prompts/registry.py:60,90`).

**Registry-compliant call sites (8):**
- `agents/rag_agent.py:54` → `get_system_prompt("rag","v1")`
- `agents/alter_ego_agent.py:103` → `get_system_prompt("alter_ego","v3")`
- `agents/outline_agent.py:62` → `render_prompt("carousel","outline")`
- `agents/content_draft_agent.py:68` → `render_prompt("carousel","content")`
- `application/services/carousel/carousel_refinement.py:74,99` → `render_prompt("refinement", …)`
- `application/tools/carousel/refine_copy.py:180` → `render_prompt("refinement","copy_rewrite")`

**Hardcoded-prompt VIOLATIONS (5 true positives):**

| # | File:line | Name | Lines | Severity |
|---|---|---|---|---|
| 1 | `agents/constants.py:39` | `TEMPLATE_ENFORCE` (persona rewrite system prompt, full `{placeholders}`) | 41 | **Critical** |
| 2 | `application/services/linkedin_post_generator.py:148` | `_build_prompt()` f-string (LinkedIn rules: 300-char, no em-dash, hashtags) | 24 | **Critical** |
| 3 | `agents/persona_agent.py:88` | `_build_style_guide()` f-string (tone/sentence/phrase rules) | 21 | **Critical** |
| 4 | `agents/quality_agent.py:53` | `_build_evaluation_prompt()` (rubric eval → JSON) | 17 | High |
| 5 | `agents/quality_agent.py:141` | `generate_improvement_suggestions()` f-string | 9 | High |

**Legit fallbacks (NOT violations):** `rag_agent.py:59` `_FALLBACK_SYSTEM_PROMPT`, `alter_ego_agent.py:45` `_ALTER_EGO_FALLBACK_PROMPT`, `infrastructure/llm/json_utils.py:18` `_JSON_REPAIR_PROMPT` (utility). These are guarded fallbacks paired with a registry call — keep, but cap length (a 9-line persona fallback drifts from `v3`; trim to a one-liner pointer like the RAG fallback).

**Note on `quality_agent.py`:** zero registry calls — the entire QA/persona-scoring prompt surface is hardcoded. This is the single most concentrated violation site.

### 1.2 Target

Move all 5 into the registry. Proposed new prompt files:

```
agents/prompts/persona/v1/enforce.yaml          # from TEMPLATE_ENFORCE  (#1, #3 merge)
agents/prompts/quality/v1/evaluate.yaml          # from _build_evaluation_prompt (#4)
agents/prompts/quality/v1/improve_suggestions.yaml  # (#5)
agents/prompts/distribution/v1/linkedin_post.yaml   # from linkedin_post_generator (#2)
```

`persona_agent.py:_build_style_guide` and `constants.py:TEMPLATE_ENFORCE` are the same conceptual prompt rendered two ways → consolidate into **one** `persona/v1/enforce.yaml` with Jinja2 vars (`persona_name`, `tone_*`, `forbidden_phrases`, `writing_samples`, …). Keep a 1-line fallback constant for registry-unavailable.

**Decision/trade-off:** the `_shared/variables.yaml` + per-domain READMEs already exist; reuse rather than invent. Persona/quality prompts must stay in sync with `skills/runtime/carousel-pipeline/_shared/` (ADR-007 three-layer alignment) — add a doc-link in each new prompt folder README.

**Enforcement (kaizen-style gate):** add a `scripts/` checker (or ruff custom) that flags multi-line string literals containing prompt markers ("You are", "INSTRUCTIONS:", "OUTPUT FORMAT") in `agents/` and `application/services/` **outside** `*fallback*` constants — with a **rule-fires regression test** on a seeded violation (CLAUDE.md AE-0180 mandate). This is the durable fix that stops regression.

---

## 2. `skills/` root organization — still-used verdicts & relocation

### 2.1 Still-used verdicts (evidence)

| Skill | Verdict | Key evidence |
|---|---|---|
| **carousel-pipeline** | **STILL USED** | Loaded by `application/services/carousel/phase_subagents.py:27-62` + `instruction_context_loader.py:101`; path const `domain/constants/runtime_skills.py:10`; copied into Docker image; CI gate `scripts/validate_skill_boundary.py`. |
| **carousel-refinement** | **STILL USED** | Refinement tools wired in `agents/rag_agent.py:138-160`; service in `application/services/carousel/refinement_service.py`; CI gate requires `SKILL.md`. |
| **knowledge-base** | **STILL USED** | `build_search_documents_tool`/`build_list_documents_tool` registered on every RAG + AlterEgo agent (`rag_agent.py:125-127`, `alter_ego_agent.py:107-119`); tools in `application/tools/knowledge_base/`; frontend module + API routes. |
| **runtime** (standalone) | **DOES NOT EXIST** | `skills/runtime/` is only a container for the three above. No `skills/runtime/runtime/`. |

> None are dead. The user's instinct ("carousel-specific skills don't belong in repo-root `skills/`") is about **placement/visibility**, not deletion. They are already physically under `skills/runtime/`; only the **root-level symlinks** (`skills/carousel-pipeline`, etc.) mix them with delivery skills.

### 2.2 Target separation

The ADR-007 boundary is already correct in principle: delivery skills under `skills/delivery/`, runtime skills under `skills/runtime/`. The mess is the **8 root symlinks** in `skills/` (delivery + runtime intermixed). Two clean options:

- **Option A (low-risk, recommended):** keep `skills/runtime/` as the home; **drop the root-level carousel/knowledge symlinks** and resolve runtime skills exclusively via `runtime_skills.py` (already the production path) + `ALTER_EGO_RUNTIME_SKILLS_ROOT`. Keep only *delivery* skill symlinks at root (those are the `/slash-command` surface). Net: root `skills/` becomes delivery-only; runtime skills are reached by code, not by symlink.
- **Option B (more aggressive):** co-locate runtime skills **with their agent package** (e.g. `backend/.../carousel_agent/skills/`) per concern 8, and point `ALTER_EGO_RUNTIME_SKILLS_ROOT` there. Bigger Docker/CI churn; do later.

**Trade-off:** the root symlinks today double as the Claude-Code `/carousel-pipeline` slash-command surface (memory: *skill slash-command registration*). If you remove them, confirm no human workflow invokes `/carousel-pipeline` as a slash command. Production code does **not** depend on the symlinks (it uses `runtime_skills.py`), so prod is unaffected — only the CI `validate_skill_boundary.py` assertion about symlinks must be updated in lockstep.

---

## 3. `agents/AGENTS.md` + `agents/` package map

### 3.1 What `agents/AGENTS.md` is — and isn't

It is a **persona/identity + delegation-rules doc** for "the Alter-Ego RAG Agent" (`agents/AGENTS.md:1-55`): identity, architecture conventions, a delegation table ("create a carousel" → `task`), tool-calling rules, safety. **It is not loaded by any code** — `grep -rn "AGENTS.md\|memory=" src/` returns **0 functional hits**. So today it's documentation drift: it describes the *intended* behavior but the agents are actually steered by `agents/prompts/rag/v1/system.md` and `alter_ego/v3/system.md`.

**Significance:** DeepAgents has a first-class `memory=` argument that **auto-loads `AGENTS.md` files** into agent context (DeepAgents docs). So `agents/AGENTS.md` is a *latent harness input* that the codebase wrote but never wired. Two coherent targets:
- **(a)** Promote it: pass `memory=[".../AGENTS.md"]` (or the harness equivalent) so it becomes real persistent context — but then it must be deduplicated against `rag/v1/system.md` (overlap risk).
- **(b)** Demote it: treat it as a human design doc and move it to `docs/architecture/` so it stops masquerading as runtime config.

Recommendation: **(a) for the RAG agent only**, scoped to delegation rules that aren't in the system prompt, OR keep it as the per-agent `memory` file in the new package layout (concern 8) — one `AGENTS.md` per agent package, intentionally loaded via `memory=`. Decide in §Open-decisions.

### 3.2 Current `agents/` package map (19 modules + prompts)

```
agents/
├── AGENTS.md                       # latent memory file (unwired)
├── rag_agent.py                    # Deep Agent (RAG + carousel tools); NO checkpointer/store
├── alter_ego_agent.py              # Deep Agent (KB-only, carousel-free); NO checkpointer/store
├── carousel_editorial_orchestrator.py  # wraps CarouselWorkflowEngine (HAS checkpointer)
├── carousel_workflow_engine.py     # graph.compile(checkpointer=…); interrupts; thread_id=project_id
├── carousel_workflow_graph.py      # StateGraph topology
├── carousel_workflow_nodes.py      # phase nodes + interrupt()  (line 129)
├── carousel_workflow.py            # re-export
├── content_draft_agent.py          # LLM subagent (registry-compliant)
├── outline_agent.py                # LLM subagent (registry-compliant)
├── source_synthesis_agent.py       # LLM subagent
├── quality_agent.py                # LLM subagent (HARDCODED prompts)
├── persona_agent.py                # persona enforce (HARDCODED prompt)
├── feedback_learning.py            # correction recording (FeedbackLearningLoop)
├── input_sanitizer.py              # text sanitation
├── chat_streaming.py               # token extraction helpers
├── constants.py                    # KEY_*, thresholds + TEMPLATE_ENFORCE (violation)
├── carousel_orchestrator/          # ORPHAN: only stale .pyc; source deleted per ADR-007 §6
└── prompts/                        # registry + alter_ego/ carousel/ rag/ refinement/ _shared/
```

**Action:** delete the orphan `agents/carousel_orchestrator/` dir (only `.pyc`; source removed by ADR-007 legacy-removal). Quick T1 cleanup.

---

## 4. Subagent delegation for carousel creation — map + taxonomy

### 4.1 Current delegation (two mechanisms, partially wired)

1. **DeepAgents `task` path (parent → subagent):** `RAGAgent._build_subagents()` (`rag_agent.py:111`) returns `[self._editorial_subagent]` if injected. The editorial subagent is built by `build_editorial_carousel_subagent()` (`application/services/carousel/editorial_subagent.py:51`) — a `StateGraph(dict)` with a single `request_node` that parses JSON (`project_id`, `topic`, …) and calls `start_workflow`. It returns a dict with `name/description/skills/runnable`. **Note:** DeepAgents subagent dicts officially take `name, description, prompt, tools, model, middleware` — this spec uses a non-standard `skills` key + a `runnable`; it works as a CompiledSubAgent but doesn't use the `tools`/`prompt` delegation surface.
2. **Phase subagent registry:** `phase_subagents.py:27` defines 4 `PhaseSubagentSpec`s (research/outline/content/caption) each carrying a `phase_skill` path + `_shared` standards. `build_phase_subagent_specs()` emits `{name, description, skills}`. These are **metadata only** — they carry skill *paths*, no executable runnable or tools. The real phase work runs as **deterministic LangGraph nodes** via `PhaseArtifactRunner` (orchestrator wires `OutlineAgent`, `ContentDraftAgent`; `carousel_editorial_orchestrator.py:40-52`).

So: the orchestrator is a **raw-LangGraph state machine** (correct per ADR-007 for deterministic phases), and the DeepAgents `task` tool is only the *entry door* (parent RAG agent → editorial subagent → starts the graph). The "subagents" in the phase registry are **descriptive context bundles**, not independently-running agents with their own tools.

### 4.2 Capability research (grounded)

DeepAgents (`>=0.5.3`) + LangGraph 1.2.5 give:
- **Custom subagents** with isolated context windows, each definable with its **own `tools`, `model`, `prompt`, `middleware`** (DeepAgents docs / DeepWiki `create_deep_agent`).
- **Built-in `task` tool** the parent calls to delegate to a named subagent; subagent runs to completion and returns **one final report** (isolated context — protects the parent's window).
- **`general-purpose`** default subagent (can be disabled).
- A subagent **can be given a web/URL tool** (any LangChain `@tool`) — the repo already owns `PlaywrightResearchTool.scrape_url` + `search_web` (`application/services/tools/research_tool.py`); these are not yet exposed as LangChain tools to a subagent.

### 4.3 Proposed subagent taxonomy (per-job, isolated context)

| Subagent | Job | Tools to grant | Skill context |
|---|---|---|---|
| `researcher` | Gather + synthesize sources; **browse a URL** during creation | `scrape_url`, `search_web` (wrap `PlaywrightResearchTool` as `@tool`), `search_documents` | `phases/research` + `_shared/critical-rules` |
| `outline_planner` | Slide plan from brief+research | (none; LLM only) | `phases/outline` |
| `content_drafter` | Slide copy w/ persona enforcement | persona-enforce tool | `phases/content` + `content-contracts`,`text-formatting` |
| `image_designer` | Image prompts + gen | `image_provider_registry` tool | `phases/images`,`image-generation` |
| `caption_writer` | IG caption + LinkedIn export | distribution tools | `phases/final-review`,`export-and-caption` |
| `qa_reviewer` | **NEW** runtime QA of the rendered carousel (see §7) | Playwright MCP nav/snapshot, `/impeccable` report tool | `_shared/anti-patterns` |

Deterministic, non-negotiable steps (design tokens, PDF export, DB sync, persona *gate* scoring) **stay as raw LangGraph nodes** (ADR-007). The taxonomy above is for the *generative/agentic* phases where isolated context + tools add value — chiefly `researcher` (URL navigation) and the new `qa_reviewer`.

**Key upgrade (URL navigation during creation):** wrap `PlaywrightResearchTool.scrape_url` and `search_web` as LangChain `@tool`s and grant them to the `researcher` subagent so the user can paste a URL and have the agent browse it mid-creation. This is the concrete answer to concern 4's "browse a URL during carousel creation."

---

## 5. Deep Agents HARNESS — extract memory / middleware / loops / checkpointers

### 5.1 Current state (evidence)

| Concern | Where | Status |
|---|---|---|
| Checkpointer build | `bootstrap/app_factory.py:133-171` `_build_checkpointer()` (postgres/sqlite/memory/disabled; AsyncExitStack lifecycle) | **Centralized** ✓ |
| Checkpointer durability guard | `bootstrap/startup_validation.py:96-121` | ✓ |
| Checkpointer consumed | only `carousel_workflow_engine.py:47` (`graph.compile(checkpointer=…)`) via orchestrator | carousel-only |
| Deep Agents (RAG, AlterEgo) | `rag_agent.py:103`, `alter_ego_agent.py:90` | **NO checkpointer / store / middleware** ✗ |
| Memory / store | none (no `BaseStore`/`InMemoryStore`); `thread_id=project_id` convention only | **absent** ✗ |
| Middleware (LangGraph) | none (`before_model`/`after_model`/`AgentMiddleware` → 0 hits); only FastAPI HTTP middleware | **absent** ✗ |
| Interrupts | `carousel_workflow_nodes.py:129` `interrupt(...)`; `Command(resume=…)` `engine.py:139,151` | carousel-only, robust ✓ |

**Narrative:** there is **no shared agent harness**. Persistence exists for the carousel graph only; the two Deep Agents are stateless across turns (history is re-fetched from the message repo each call and replayed — `rag_agent.py:181-198`). No long-term memory/store, no summarization middleware (so long chats grow unbounded into the model window), no HITL middleware on the Deep Agents.

### 5.2 Target harness (`agents/harness/` shared package)

Create `backend/src/rag_backend/agents/harness/` exposing one composition surface both Deep Agents and the carousel orchestrator consume:

```
agents/harness/
├── __init__.py            # public API
├── checkpointer.py        # MOVE _build_checkpointer() here; CheckpointerProvider Protocol + factory
├── store.py               # NEW: BaseStore provider (Postgres/InMemory) for long-term memory
├── memory.py              # NEW: load per-agent AGENTS.md as memory=; conversation summarization config
├── middleware.py          # NEW: SummarizationMiddleware + HumanInTheLoopMiddleware presets; custom AgentMiddleware base
├── interrupts.py          # MOVE interrupt parsing/_iter_interrupt_values/_merge_… from engine
├── builder.py             # build_deep_agent(config): wraps create_deep_agent w/ checkpointer+store+middleware+memory
└── config.py              # DeepAgentConfig dataclass (model, tools, subagents, system_prompt, memory, checkpointer, store, middleware)
```

**What each agent gains:**
- **RAG/AlterEgo Deep Agents** → optional checkpointer + `SummarizationMiddleware` (caps window growth on long chats) + a `BaseStore` for long-term memory. Today they replay history manually; with a checkpointer keyed by `thread_id=conversation_id`, history replay can be simplified.
- **Carousel orchestrator** → keeps its raw-LangGraph graph but pulls the checkpointer + interrupt helpers from the harness instead of inlining them.

**Capability grounding:** DeepAgents `create_deep_agent` accepts `checkpointer`, `store`, `middleware`, `memory` kwargs; LangGraph 1.2 ships `SummarizationMiddleware` (threshold-triggered history compression) and `HumanInTheLoopMiddleware` (`interrupt_on` tool gating). The harness just *presets* these. (Sources below.)

**Trade-off / risk:** giving the chat Deep Agents a checkpointer changes persistence semantics (now there are TWO sources of truth: the message repo *and* the LangGraph checkpoint). Pick one as canonical (recommend: checkpoint for in-flight thread state, message repo for durable history/audit) and document it as an ADR. Don't dual-write blindly (memory: *AE-0163 dual-write* hazard).

---

## 6. Improvement loop — runtime memory/chat → handoff → kaizen

### 6.1 Current (delivery side)

`/handoff` (`skills/handoff-skill/SKILL.md`) writes `.agent/handoff/HANDOFF-latest.{md,json}`; `scripts/handoff/log_learnings.py` distils problems/landmines/decisions into append-only `.agent/handoff/learnings-log.jsonl`; `/kaizen-skill session` mines that log into proposed rules/gates/tickets (human-approved). This is for **code-delivery sessions**, not product runs.

### 6.2 Target (runtime/product side) — parallel, not merged

Add a **runtime kaizen channel** that mirrors the delivery one but keyed on *carousel creation sessions*:

1. **Session summary source:** the harness `store.py` (long-term memory) + chat history per `conversation_id`/`project_id`. On carousel completion (or user `/handoff`-equivalent), emit a structured **run summary** (brief, phases, revisions, reviewer feedback, QA report from §7) to `.agent/handoff/runtime-learnings-log.jsonl` (separate file → keeps delivery vs product signal distinct).
2. **KAIZEN runtime agent (user-run):** a thin variant of `kaizen-skill` (`session` mode) that mines `runtime-learnings-log.jsonl` → proposes improvements to **prompts/skills standards** (`_shared/*.md`, `agents/prompts/*`), persona forbidden-phrases, and subagent instructions — human-approved before any change. This closes ADR-003's feedback loop at the *standards* level, complementing `FeedbackLearningLoop` which closes it at the *per-correction* level.

**Why parallel, not unified:** delivery kaizen mutates lint rules/CI gates/CLAUDE.md; runtime kaizen mutates content standards/prompts. Same *shape* (signal log → root-cause → human-approved emission), different *targets*. Sharing the JSONL would pollute both. Reuse the `kaizen-skill` engine, swap the input log + the emission catalog.

---

## 7. Runtime QA subagent (product QA of a created carousel)

### 7.1 Current

No runtime/product QA. `quality_agent.py` scores *text* against a rubric (and is itself a prompt-hardcoding violation). Playwright exists only for **export geometry** (`infrastructure/external/playwright_export.py`, `playwright_geometry.py`) — not for QA navigation. Playwright **MCP** browser tools are available to the harness environment.

### 7.2 Target — `qa_reviewer` subagent (distinct from delivery `qa-agent`)

A harness subagent that, after a carousel renders, **drives Playwright MCP** to open the carousel preview, snapshot each slide, and produce an `/impeccable`-style report: visual/typography checks vs `_shared/design-system.md`, anti-pattern checks vs `_shared/anti-patterns.md`, caption/hashtag checks vs `_shared/export-and-caption.md`, voice-score via persona rubric. Output = a concrete **improvement list** that feeds the §6 runtime run summary → `runtime-learnings-log.jsonl`.

- **Tools:** Playwright MCP (`browser_navigate`, `browser_snapshot`, `browser_take_screenshot`), a `report` tool that writes the structured QA artifact.
- **Boundary:** keep strictly separate from `skills/delivery/qa-agent` (that validates *code*; this validates *generated artifacts*). Name it `qa_reviewer` / `impeccable` to avoid confusion.
- **Wiring:** runs as a final deterministic node OR a `task`-delegated subagent after `final-review`. Recommend a node (deterministic trigger) that *internally* may call the LLM for the qualitative report.

**Trade-off:** Playwright-in-prod for QA adds runtime cost + a browser dependency on the hot path. Gate it behind a flag (QA-on-demand or sampled), not every generation.

---

## 8. Target folder structure — per-agent packages vs Clean Architecture

### 8.1 The tension

The user wants:
```
alter_ego_agent/  { skills/ tools/ agents/ utils/ prompts/ }
carousel_agent/   { skills/ tools/ agents/ utils/ prompts/ }
```
Clean Architecture (ADR-009, `backend/CLAUDE.md`) mandates `domain → application → infrastructure → api`, with business logic in `application/services` + `application/tools`, and agents that "orchestrate, don't implement" (`agents/AGENTS.md:17-19`). A self-contained `carousel_agent/` holding `tools/` (which today live in `application/tools/carousel/` and call infra) would **straddle layers** and break the import-direction rule.

### 8.2 Reconciliation (recommended)

Treat each per-agent package as a **composition/orchestration slice** that *references* (not *absorbs*) the Clean-Architecture layers. Map the user's sub-folders onto existing code:

| User folder | Maps to | Placement |
|---|---|---|
| `agents/` | the Deep/LangGraph agent classes + subagent specs | `…/agents/<agent>/` (orchestration only) |
| `prompts/` | already exists | keep under `agents/prompts/<domain>/` (shared registry) — do **not** fork per agent |
| `tools/` | tool **builders** (closures over services) | stay in `application/tools/<domain>/`; agent package imports the builders |
| `skills/` | runtime skill markdown | `skills/runtime/<skill>/` (or co-located later, Option B §2.2) |
| `utils/` | helpers (`chat_streaming`, `input_sanitizer`) | small per-agent `utils.py` is fine (pure helpers, no infra) |

**Proposed layout under `backend/src/rag_backend/agents/`:**
```
agents/
├── harness/                # §5 — shared (checkpointer/store/memory/middleware/interrupts/builder)
├── prompts/                # shared registry (unchanged location)
├── alter_ego_agent/        # AGENTS.md (memory), agent.py, utils.py  (KB-only)
├── carousel_agent/         # agent.py (orchestrator), subagents/ (taxonomy §4.3), nodes/, utils.py
└── shared/                 # persona/quality/feedback agents reused by multiple packages
```
`tools/` and the heavy carousel `application/services/carousel/*` (70+ files) **stay in `application/`** — the agent packages import their builders. This keeps Clean Architecture intact while giving the user the per-agent *mental model* they want.

**Conflict to flag:** literally moving `application/tools/` or services into `agents/<agent>/tools/` would invert dependencies (agents would contain infra-touching code) and violate ADR-009 + the 400-line/3-arg rules' spirit. **Do not** do that. The per-agent package is an *orchestration façade*, not a vertical slice that owns persistence.

---

## 9. Migration sequence (phased, low-risk) + effort tiers

| Phase | Work | Tier | Risk |
|---|---|---|---|
| **P0** | Delete orphan `agents/carousel_orchestrator/` (stale `.pyc`). Decide `AGENTS.md` promote/demote. | T1 | none |
| **P1** | Prompt consolidation: move 5 hardcoded prompts → registry (`persona/`, `quality/`, `distribution/`); trim fallbacks; add anti-hardcoded-prompt checker + **rule-fires test** (AE-0180). | T2 | low (pure refactor, behavior-preserving; needs char-for-char prompt parity tests) |
| **P2** | Skills relocation: drop root carousel/knowledge symlinks (Option A), make `skills/` root delivery-only, update `validate_skill_boundary.py` + CI in lockstep. | T2 | low-med (CI gate + slash-command surface) |
| **P3** | Harness extraction: create `agents/harness/`; move `_build_checkpointer` + interrupt helpers; add store/memory/middleware presets; `build_deep_agent()` builder. Carousel engine + Deep Agents consume harness. | T3 | med (touches bootstrap + both agents; needs ADR) |
| **P4** | Subagent taxonomy: wrap `PlaywrightResearchTool` as `@tool`; give `researcher` URL-nav; align subagent specs to DeepAgents `tools`/`prompt` fields. | T3 | med |
| **P5** | Per-agent packages: introduce `alter_ego_agent/`, `carousel_agent/`, `shared/` façades (imports only; no infra moves). | T2 | med (import churn; many call sites) |
| **P6** | Runtime QA subagent (`qa_reviewer` + Playwright MCP + report tool), flag-gated. | T3 | med |
| **P7** | Runtime improvement loop: `runtime-learnings-log.jsonl` + kaizen runtime mode; wire QA report → run summary. | T2 | low |

Sequence rationale: **P1/P2 first** (independent, high-value, low-risk, no ADR) → **P3 harness** (unlocks P4/P6) → packages last (P5) since they're pure reorganization that benefits from the harness existing.

---

## 10. Proposed ADRs

| ADR | Title | One-line rationale |
|---|---|---|
| ADR-013 | All agent prompts loaded via the registry (no inline prompts) | Promote the CLAUDE.md standard to an enforced, gated decision; persona/quality/distribution move to `.yaml`. |
| ADR-014 | Shared Deep Agents harness (checkpointer + store + memory + middleware) | One composition surface for all agents; defines canonical persistence source (checkpoint vs message repo). |
| ADR-015 | Subagent taxonomy + URL-navigation tool for carousel creation | Per-job isolated-context subagents; `researcher` gets web/URL tools. |
| ADR-016 | Per-agent orchestration packages over Clean Architecture | Agent packages are façades; tools/services stay in `application/`; codifies the non-conflict rule. |
| ADR-017 | Runtime product-QA subagent + runtime kaizen loop (distinct from delivery QA/kaizen) | Playwright-MCP QA of generated carousels feeds a separate runtime-learnings loop. |
| ADR-018 (optional) | Skills layout: runtime skills resolved by code, root `skills/` is delivery-only | Removes symlink intermixing; updates the boundary CI gate. |

---

## 11. Open decisions for the human

1. **`AGENTS.md` — promote or demote?** Wire it as a DeepAgents `memory=` file (real runtime context, must dedupe vs `rag/v1/system.md`) **or** move it to `docs/architecture/` as a design doc. Today it's neither (unwired). *(My lean: per-agent `memory` file in the new package layout.)*
2. **Canonical persistence for chat Deep Agents** once they get a checkpointer: LangGraph checkpoint vs the existing message repository — which is source of truth, and do we stop manual history replay? (Dual-write is the AE-0163 hazard.)
3. **Skills relocation aggressiveness:** Option A (drop root symlinks, code-resolves runtime skills — recommended) vs Option B (co-locate skills inside the agent package, bigger Docker/CI churn). Also: is `/carousel-pipeline` used as a human slash command? If yes, A removes it.
4. **Runtime QA cost posture:** Playwright-MCP QA on every generation vs sampled/on-demand (browser on the hot path = latency + cost).
5. **Per-agent package scope:** strict façade (imports only — recommended, preserves Clean Arch) vs the user's literal vertical slice (`tools/` inside the agent package, which violates ADR-009). Need an explicit ruling so P5 doesn't drift.
6. **Persona/quality prompt consolidation:** merge `TEMPLATE_ENFORCE` + `_build_style_guide` into one `persona/v1/enforce.yaml` (they're the same prompt rendered twice) — confirm no behavioral divergence between the two today.

---

## 12. Skeptical self-check (where this could be wrong / over-engineered)

- **Harness may be premature for 2 agents.** A full `harness/` package (8 modules) for two Deep Agents + one carousel graph risks gold-plating. Counter: checkpointer is *already* centralized; the harness mostly *relocates* + adds 2 presets (summarization, store). Keep it minimal — resist building `agent_factory`/`BootstrapHarness` abstractions nobody consumes yet.
- **Subagent taxonomy vs ADR-007's "deterministic nodes."** ADR-007 deliberately made phases *deterministic LangGraph nodes*, not autonomous subagents. Converting them to `task`-delegated subagents could regress the determinism/HITL guarantees. **Mitigation:** only `researcher` (needs URL nav) and `qa_reviewer` (qualitative) become true subagents; the rest stay nodes. Don't over-agentify.
- **Checkpointer for chat may add more state-sync bugs than it solves.** Manual history replay is simple and auditable. If long-context isn't a real pain yet, just add `SummarizationMiddleware` and skip the chat checkpointer (defer Open-decision #2).
- **Prompt extraction parity risk.** Moving f-string prompts to Jinja2 YAML can silently change whitespace/ordering → drift in model output. Mandate **golden-output parity tests** (render == old f-string) before/after, or it's a behavior change masquerading as a refactor.
- **Removing root symlinks could break a human's `/carousel-pipeline` muscle memory** (memory: slash-command registration needs a symlink). Verify before P2.
- **`runtime-learnings-log.jsonl` may never accumulate enough signal** to justify a second kaizen channel for a single-user product. Could start as a manual review of QA reports; formalize the loop only if volume warrants.
- **AGENTS.md promotion could double-instruct** the model (system prompt + memory file overlap) → token waste + contradictory steering. Dedupe is mandatory if promoted.

---

## Sources (capability research)

- DeepAgents repo — *batteries-included agent harness* (subagents w/ isolated context, filesystem/HITL/summarization middleware, checkpointing): https://github.com/langchain-ai/deepagents
- DeepAgents overview docs — `create_deep_agent` kwargs (`subagents`, `middleware`, `checkpointer`, `store`, `memory`/AGENTS.md, `interrupt_on`, `permissions`); `task` tool; `general-purpose` subagent; `StateBackend`/`StoreBackend`/`CompositeBackend`: https://docs.langchain.com/oss/python/deepagents/overview
- DeepWiki `create_deep_agent` (subagent dict fields `name/description/prompt/tools/model/middleware`): https://deepwiki.com/langchain-ai/deepagents/5.1-create_deep_agent
- LangChain middleware docs — `AgentMiddleware` (`before_model`/`after_model`/`modify_model_request`), `SummarizationMiddleware`, `HumanInTheLoopMiddleware` (`interrupt_on`): https://docs.langchain.com/oss/python/langchain/middleware
- Local pins: `backend/uv.lock` → `deepagents>=0.5.3`, `langgraph==1.2.5`.
```
