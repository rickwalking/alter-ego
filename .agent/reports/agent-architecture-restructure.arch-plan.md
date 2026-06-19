# Agent Architecture Restructure — Research + Plan (Architect)

**Mode:** architect / research+plan (read-only on production code)
**Author:** Architect skill
**Date:** 2026-06-18
**Repo:** alter-ego
**Scope:** prompt consolidation, runtime-skills relocation, `AGENTS.md` semantics, subagent taxonomy, a reusable Deep Agents harness (memory/middleware/checkpointer/store), the improvement loop, a runtime QA subagent, and a per-agent modular package layout — reconciled with Clean Architecture (ADR-009) and the DeepAgents consolidation (ADR-007).

> Dependency facts (pinned): `deepagents >= 0.5.3`, `langgraph == 1.2.5` (`backend/uv.lock`). DeepAgents `create_deep_agent` supports kwargs `model, tools, system_prompt, subagents, middleware, checkpointer, store, interrupt_on, permissions, memory` (memory = auto-loaded `AGENTS.md` files). **The `checkpointer=` kwarg acceptance MUST be build-time verified** (see Revision 2 §B1). Sources cited at the bottom.

---

## Revision 2 — post-skeptical (2026-06-18)

External cold-critic verdict was **BLOCK**; five current-state premises were re-verified against live code and the corrections are folded in below. Status of each prior BLOCK finding → revised:

| # | BLOCK finding | Prior plan claim | Revised status |
|---|---|---|---|
| 1 | **Current-state facts wrong** | `skills/runtime/` "empty container"; both chat agents "stateless"; "5 hardcoded prompts"; `carousel_orchestrator/` "stale .pyc" | **CORRECTED.** `skills/runtime/` has **20 files** incl. `_shared/` standards cross-referenced by phase skills. Chat agents are **already stateful** — they persist every message to `message_repository` and rebuild history from Postgres. Hardcoded prompts = **4 active + 1 dead** (`TEMPLATE_ENFORCE`, `constants.py:39`, no importer → **delete**). `carousel_orchestrator/` dir **exists but is empty** (no source). Counts/estimates in §0/§1/§3 adjusted. |
| 2 | **Source-of-truth was "open"** | Open-decision #2 (defer to P3) | **PROMOTED TO BLOCKER gating P3/B1.** Resolve the source-of-truth ADR FIRST. The checkpointer must **REPLACE** `message_repository` persistence (or a documented one-way sync) — **never dual-write** (AE-0163 class). Build-time check that `create_deep_agent` (graph.py:218) accepts `checkpointer=`; else use the documented alternative. See §5.3 + §9 sequencing. |
| 3 | **P2 skills move under-scoped** | "drop root symlinks" one-liner | **PRECONDITION ADDED.** Audit `_shared/` cross-refs + every load path and produce a **skill→file dependency graph BEFORE moving anything** (a wrong move = prod `FileNotFoundError` on auto-deploy). Confirm repo-root symlinks aren't consumed by prod (code resolves `get_runtime_skills_filesystem_root()`); if dead, drop them. See §2.3. |
| 4 | **B2/B3 split-brain** | informal "skills here, tools there" | **FORMAL skill/tool contract.** skill = what the agent reads (lives in the agent package); tool = a LangChain `@tool` adapter delegating to an `application/` service via Protocol. Single-agent adapters MAY live in the agent package; `application/tools/` keeps only genuinely shared tools. See §8.3. |
| 5 | **Runtime QA (B6) blocking risk** | "flag-gated / sampled" | **Best-effort / non-blocking, every-generation.** Report to a side table; a Playwright crash/timeout must NOT fail the user's generation; revisit sampled cadence after a baseline week; scope the report contents (LLM-scored reviewer doubles per-gen cost). See §7.2. |
| — | **DeepSeek** | (was advisory/optional in feasibility note) | **RETAINED as a COMMITTED first-class part of the plan via ADR-019 (tiered model selection).** Execution detail corrected: deterministic phase→model map (NOT `.with_fallbacks` as the tier boundary); primary/fallback Langfuse tag; A/B parity check vs the ≥70 persona gate before committing each phase. Pilot sourced via opencode Zen "Go" gateway; **production sourcing is an OPEN DECISION** (Zen vs direct DeepSeek API). See §13 + ADR-019 + Open-decision #2. |

---

## 0. Executive verdicts (jump table)

| Concern | Verdict |
|---|---|
| 1. Hardcoded prompts | **4 active violations + 1 dead** (worst active: `linkedin_post_generator.py` / `persona_agent.py` / `quality_agent.py`). `agents/constants.py:39` `TEMPLATE_ENFORCE` (41 lines) has **no importer → delete it** (do not migrate). `quality_agent.py` is 100% off-registry. |
| 2. skills/ root org | `carousel-pipeline`, `carousel-refinement`, `knowledge-base` are **ALL STILL USED** at runtime. `skills/runtime/` is **NOT empty — it holds 20 files** (5 phase `SKILL.md` + 6 `_shared/*.md` + contracts/manifest), with `_shared/` standards **cross-referenced by the phase skills** (relocation coupling). `runtime` standalone skill **does not exist** (container dir only). They *do* belong in the repo but should be cleanly fenced from delivery skills. |
| 3. `agents/AGENTS.md` | A persona/identity doc that **is NOT loaded by any code** (`grep` → 0 hits). It is a *latent* DeepAgents `memory=` file, not a wired system prompt. |
| 4. Subagent delegation | Two parallel mechanisms today; the DeepAgents `task`/subagent path is **half-wired** (specs carry `skills` but no `tools`/`runnable`/`model`). |
| 5. Harness | **No shared harness.** Checkpointer is centralized in `bootstrap/app_factory.py` but only the carousel engine consumes it; both Deep Agents run with **no checkpointer/store/middleware**. **NOTE:** the two chat agents are **NOT stateless** — they already persist every message to `message_repository` and rebuild history from Postgres, so adding a checkpointer creates a **second write path (AE-0163 dual-write hazard)** that the source-of-truth ADR must resolve FIRST. |
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

**Hardcoded-prompt findings: 4 ACTIVE violations to remediate + 1 DEAD to delete.**

| # | File:line | Name | Lines | Action |
|---|---|---|---|---|
| 1 | `agents/constants.py:39` | `TEMPLATE_ENFORCE` (persona rewrite system prompt, full `{placeholders}`) | 41 | **DELETE — dead code, no importer** (re-verified: `grep -rn TEMPLATE_ENFORCE src/` → 0 importers). Do **not** migrate it to the registry. |
| 2 | `application/services/linkedin_post_generator.py:148` | `_build_prompt()` f-string (LinkedIn rules: 300-char, no em-dash, hashtags) | 24 | **Critical** — migrate to registry |
| 3 | `agents/persona_agent.py:88` | `_build_style_guide()` f-string (tone/sentence/phrase rules) | 21 | **Critical** — migrate to registry |
| 4 | `agents/quality_agent.py:53` | `_build_evaluation_prompt()` (rubric eval → JSON) | 17 | High — migrate to registry |
| 5 | `agents/quality_agent.py:141` | `generate_improvement_suggestions()` f-string | 9 | High — migrate to registry |

> **Corrected count (Revision 2):** the prior "5 true violations" framing was wrong. `TEMPLATE_ENFORCE` is **dead** (no importer) → it is **deleted, not migrated**. So P1 migrates **4 active** prompts (#2–#5) and **deletes 1** (#1). The persona-enforce registry file is therefore sourced from `persona_agent.py:_build_style_guide` (#3), NOT from the dead `TEMPLATE_ENFORCE`.

**Legit fallbacks (NOT violations):** `rag_agent.py:59` `_FALLBACK_SYSTEM_PROMPT`, `alter_ego_agent.py:45` `_ALTER_EGO_FALLBACK_PROMPT`, `infrastructure/llm/json_utils.py:18` `_JSON_REPAIR_PROMPT` (utility). These are guarded fallbacks paired with a registry call — keep, but cap length (a 9-line persona fallback drifts from `v3`; trim to a one-liner pointer like the RAG fallback).

**Note on `quality_agent.py`:** zero registry calls — the entire QA/persona-scoring prompt surface is hardcoded. This is the single most concentrated violation site.

### 1.2 Target

Move the **4 active** prompts into the registry and **delete the dead one**. Proposed new prompt files:

```
agents/prompts/persona/v1/enforce.yaml          # from persona_agent.py:_build_style_guide (#3)
agents/prompts/quality/v1/evaluate.yaml          # from _build_evaluation_prompt (#4)
agents/prompts/quality/v1/improve_suggestions.yaml  # (#5)
agents/prompts/distribution/v1/linkedin_post.yaml   # from linkedin_post_generator (#2)
```

**Corrected (Revision 2):** `constants.py:TEMPLATE_ENFORCE` (#1) is **dead code** — re-verified to have **no importer** — so it is **deleted outright**, not merged. The persona-enforce registry file (`persona/v1/enforce.yaml`) is sourced **only** from the live `persona_agent.py:_build_style_guide` (#3), rendered with Jinja2 vars (`persona_name`, `tone_*`, `forbidden_phrases`, `writing_samples`, …). Keep a 1-line fallback constant for registry-unavailable. (Sanity-check at implementation that nothing referenced `TEMPLATE_ENFORCE` indirectly before deleting; the grep says no.)

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

### 2.3 Precondition (BLOCKER for P2): skill→file dependency graph BEFORE any move

> **Revision 2 — corrected current state:** `skills/runtime/` is **NOT empty**. `find skills/runtime -type f` = **20 files**: 5 phase `SKILL.md` + 6 `_shared/*.md` standards + contracts/manifest. The phase skills **cross-reference the `_shared/*.md` standards by relative path**, so the runtime skills are a coupled tree, not loose files. The human decision (decisions.md #2) is to **co-locate** these into their owning agent package — a higher-touch move than "drop symlinks". Because **prod auto-deploys** (CLAUDE.md), a wrong/incomplete move is a production `FileNotFoundError` at request time.

**Mandatory precondition AC — before moving a single file, produce a skill→file dependency graph that audits ALL of:**

1. `_shared/` cross-references *inside* the skill markdown (every relative link/`@include` between a phase `SKILL.md` and a `_shared/*.md`) — moving a phase skill without its `_shared` siblings breaks the reference.
2. `application/services/carousel/phase_subagents.py` (loads phase-skill paths).
3. `application/services/.../instruction_context_loader.py` (`:101` skill-context load).
4. `domain/constants/runtime_skills.py` (path constants + `get_runtime_skills_filesystem_root()`).
5. **Dockerfile** copy path(s) into `/app/skills/runtime` (the prod resolution root).
6. The **CI skill-path gate** (`scripts/validate_skill_boundary.py` + any skill-path check).

**Then:** every relocation ticket must update **all six** in lockstep, and the move is verified by (a) building the Docker image and resolving each skill path inside it, and (b) running the CI skill-path gate green — not just a passing local tree.

**Repo-root symlinks:** confirmed **NOT consumed by any prod path** — prod resolves skills via `get_runtime_skills_filesystem_root()` (code), never the root symlinks. They are therefore **dead for production**; drop them (after the `/carousel-pipeline` slash-command check, Open-decision #3) and do **not** let their layout shape the co-located target tree.

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
├── carousel_orchestrator/          # ORPHAN: dir exists but EMPTY (no source); source removed per ADR-007 §6
└── prompts/                        # registry + alter_ego/ carousel/ rag/ refinement/ _shared/
```

**Action:** delete the orphan `agents/carousel_orchestrator/` dir (it **exists but is empty** — no source; source removed by ADR-007 legacy-removal). Quick T1 cleanup.

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

**Narrative:** there is **no shared agent harness**. LangGraph-checkpoint persistence exists for the carousel graph only. **Correction (Revision 2): the two chat Deep Agents are NOT stateless.** They **already persist every message to `message_repository`** (`rag_agent.py:198,277,315`; `alter_ego_agent.py:147,223,261`) and **rebuild history from Postgres each turn** (`rag_agent.py:181`, `alter_ego_agent.py:130`). What they lack is a *LangGraph checkpointer/store/middleware* — not state. This matters: adding a checkpointer keyed by `thread_id=conversation_id` introduces a **SECOND durable write path** alongside the existing `message_repository`, i.e. the **AE-0163 dual-write hazard**. That is why the source-of-truth decision is now a **BLOCKER gating this phase** (§5.3), not an afterthought. They also lack long-term memory/store and summarization middleware (so long chats grow unbounded into the model window) and HITL middleware.

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

**Trade-off / risk:** giving the chat Deep Agents a checkpointer changes persistence semantics (now there are TWO durable write paths: the existing `message_repository` *and* the LangGraph checkpoint). This is resolved in §5.3 as a **blocking precondition**, not a free choice made during implementation.

### 5.3 BLOCKER — source-of-truth ADR gates the harness (P3/B1)

> **Revision 2:** what was "Open-decision #2 (defer to P3)" is now a **hard sequencing BLOCKER**. The harness (P3) MUST NOT wire a chat-agent checkpointer until the source-of-truth ADR is **accepted**.

**Rule (sequence): ADR (source-of-truth) → harness. Never harness-then-ADR.**

The ADR MUST decide: **is the LangGraph checkpoint or `message_repository` canonical?** The only two acceptable outcomes:

1. **Checkpointer REPLACES `message_repository` persistence** for in-flight thread state — the chat agents stop their manual `message_repository.create(...)` writes and history is rebuilt from the checkpoint. (Durable audit/history may still be derived, but via a documented one-way sync, not a parallel write.)
2. **A documented one-way sync** (checkpoint → message_repository, OR message_repository → checkpoint) with a single writer.

**Forbidden:** dual-write (both paths writing independently). That is the exact AE-0163 failure class (data divergence + breakage) called out in project memory.

**Build-time capability check (mandatory before B1):** verify that `deepagents.create_deep_agent` (the call at `graph.py:218`) **actually accepts a `checkpointer=` kwarg** at the pinned version (`deepagents>=0.5.3`). If it does **not**, B1 needs an alternative integration — compile the underlying graph with `.compile(checkpointer=…)` directly (as the carousel engine already does, `carousel_workflow_engine.py:47`), or pin/patch the library — documented in the ADR's "consequences". Do **not** assume the kwarg exists.

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

### 7.3 Best-effort / non-blocking contract (Revision 2)

The human decision (decisions.md #4) is **every generation** — that is retained — **but it is BEST-EFFORT and MUST NOT block the user's generation.** Hard requirements:

- **Non-blocking:** runs **after** the generation completes and the artifact is delivered to the user; the QA report **attaches post-generation** (to a side table / async channel), it is **never** on the critical path of the response.
- **Crash-safe:** a Playwright crash, hang, or timeout (droplet Chromium has precedent — see the `InMemorySaver` fallback at `app_factory.py:167`) **MUST be swallowed** — the generation is already done and succeeds regardless. Wrap the QA node in a guard that records a "QA-unavailable" marker and moves on. **A QA failure can never fail a generation.**
- **Side-table reporting:** write the structured report to a **dedicated side table** (e.g. `carousel_qa_reports`, keyed by `project_id`) + the §6 `runtime-learnings-log.jsonl`. Do not mutate the carousel record's success state.
- **Report scope (decide explicitly):** at minimum **screenshot + DOM snapshot + rule-checks** (design-system/anti-patterns/caption-rules). An **LLM-scored** qualitative reviewer is *optional* and **roughly doubles per-generation cost** (a second model pass per carousel) — call it out in the ADR and gate it separately from the cheap screenshot/DOM/rule pass.
- **Cadence revisit:** ship "every generation" first to gather a baseline, then **reconsider sampled cadence after a baseline week** if cost/latency/volume warrant — captured as a follow-up review, not a blocker.

**Why not flag-gated/sampled up front:** the human chose every-generation for full signal; the safety comes from the non-blocking + crash-safe contract above, not from skipping generations.

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

### 8.3 FORMAL skill/tool contract (Revision 2 — resolves the B2/B3 split-brain)

The "skills co-located in the agent package but tools in `application/`" split was informal and ambiguous. Make it a **rule**:

- **Skill = what the agent READS.** Markdown instruction/standards context (phase `SKILL.md`, `_shared/*.md`). It is *content*, has no Python imports, and **lives in the agent package** it belongs to (decisions.md #2 co-location).
- **Tool = a LangChain `@tool` ADAPTER.** A thin function that **delegates to an `application/` service via a Protocol** — it owns **no** business logic and **no** infra. The service (and its infra dependencies) stay in `application/` / `infrastructure/`, preserving Clean Architecture (ADR-009).
- **Placement rule for tool adapters:**
  - A tool adapter used by **exactly one agent** MAY live **in that agent's package** (e.g. `carousel_agent/tools/…`) — it's a thin façade over an `application/` service, so it does not import infra.
  - `application/tools/` keeps **only genuinely shared tools** (used by ≥2 agents, e.g. the `knowledge_base` search/list tools on both RAG + AlterEgo).
- **Invariant:** no matter where the *adapter* lives, the **business logic + infra stay in `application/`/`infrastructure/` behind a Protocol**. The agent package never contains persistence, network, or DB code — only orchestration, prompts, skills (content), and thin tool adapters.

This is the explicit ruling that prevents the per-agent packages from drifting into vertical slices that own infra.

---

## 9. Migration sequence (phased, low-risk) + effort tiers

| Phase | Work | Tier | Risk |
|---|---|---|---|
| **P0** | Delete orphan `agents/carousel_orchestrator/` (**empty dir, no source**). Decide `AGENTS.md` promote/demote (decisions.md #3 → wire as per-agent `memory=`). | T1 | none |
| **P1** | Prompt consolidation: migrate **4 active** hardcoded prompts → registry (`persona/`, `quality/`, `distribution/`); **DELETE the dead `TEMPLATE_ENFORCE`**; trim fallbacks; add anti-hardcoded-prompt checker + **rule-fires test** (AE-0180). | T2 | low (behavior-preserving; needs char-for-char golden-output parity tests) |
| **P2** | Skills relocation (**co-locate**, decisions.md #2): **FIRST** produce the skill→file dependency graph (§2.3 precondition — `_shared/` cross-refs + all 6 load paths); then move runtime skills into their agent package and update `runtime_skills.py`, `phase_subagents.py`, `instruction_context_loader.py`, Dockerfile `/app/skills/runtime`, CI skill-path gate **in lockstep**; drop dead root symlinks; make root `skills/` delivery-only. Verify by Docker-image path resolution + green CI gate. | T2 | **med** (higher-touch than prior "drop symlinks"; prod auto-deploys → a wrong move = `FileNotFoundError`) |
| **ADR-019** | **DeepSeek tiered model pilot (committed)** — lands **after P1**. Deterministic phase→model map; pilot `SourceSynthesisAgent` (research) via opencode Zen "Go"; A/B parity check vs ≥70 persona gate before committing; Langfuse primary/fallback tag; integration-test JSON/tool-calling through the chosen endpoint. Keep Claude on content/caption/persona. See §13. | T2 | low-med (additive wiring + settings + parity tests; no graph topology change) |
| **source-of-truth ADR** | **BLOCKER gating P3.** Decide checkpoint-vs-`message_repository` canonical (replace, or one-way sync — **never dual-write**); build-time check `create_deep_agent` accepts `checkpointer=`. Must be **accepted before P3 begins**. See §5.3. | T1 (decision) | — (gates P3) |
| **P3** | Harness extraction: create `agents/harness/`; move `_build_checkpointer` + interrupt helpers; add store/memory/middleware presets; `build_deep_agent()` builder. Carousel engine + Deep Agents consume harness. **Chat-agent checkpointer wiring only after the source-of-truth ADR is accepted.** | T3 | med (touches bootstrap + both agents; **gated on source-of-truth ADR**) |
| **P4** | Subagent taxonomy: wrap `PlaywrightResearchTool` as `@tool`; give `researcher` URL-nav; align subagent specs to DeepAgents `tools`/`prompt` fields. | T3 | med |
| **P5** | Per-agent façade packages: introduce `alter_ego_agent/`, `carousel_agent/`, `shared/` (orchestration + prompts + skills + thin tool adapters per §8.3; **no infra moves**); per-agent `memory=` AGENTS.md. | T2 | med (import churn; many call sites) |
| **P6** | Runtime QA subagent (`qa_reviewer` + Playwright MCP + report tool), **every-generation but best-effort/non-blocking** (§7.3): side-table report, crash-safe, revisit sampled cadence after a baseline week. | T3 | med |
| **P7** | Runtime improvement loop: `runtime-learnings-log.jsonl` + kaizen runtime mode; wire QA report → run summary. | T2 | low |

**Sequence rationale (Revision 2):**
- **P1 (prompts) + corrected P2 (skills co-location) first** — high-value, low-ADR; P2 is now gated on its own dependency-graph precondition (§2.3).
- **ADR-019 DeepSeek pilot lands right after P1** — P1 moves `quality_agent`'s prompt to the registry, so you don't bake a cheap model onto a hardcoded prompt; the pilot is additive and does not block the restructure.
- **P3 harness is BLOCKED on the source-of-truth ADR** — resolve checkpoint-vs-`message_repository` **before** wiring any chat-agent checkpointer (no dual-write). The harness then unlocks P4/P6.
- **Packages last (P5)** — pure reorganization that benefits from the harness existing.

---

## 10. Proposed ADRs

| ADR | Title | One-line rationale |
|---|---|---|
| ADR-013 | All agent prompts loaded via the registry (no inline prompts) | Promote the CLAUDE.md standard to an enforced, gated decision; persona/quality/distribution move to `.yaml`; the dead `TEMPLATE_ENFORCE` is deleted, not migrated. |
| **ADR-014a** | **Source-of-truth for chat-agent persistence (checkpoint vs `message_repository`)** — **BLOCKER, accept BEFORE the harness (P3)** | Decides which is canonical; checkpointer must **replace** `message_repository` writes (or a documented one-way sync); **dual-write is forbidden** (AE-0163 class). Includes the build-time `checkpointer=` capability check. |
| ADR-014 | Shared Deep Agents harness (checkpointer + store + memory + middleware) | One composition surface for all agents; **consumes the ADR-014a source-of-truth decision** — does not re-open it. |
| ADR-015 | Subagent taxonomy + URL-navigation tool for carousel creation | Per-job isolated-context subagents; `researcher` gets web/URL tools. |
| ADR-016 | Per-agent orchestration packages over Clean Architecture + **formal skill/tool contract** | Agent packages are façades; skill = content the agent reads (in the package); tool = `@tool` adapter delegating to an `application/` service via Protocol; single-agent adapters MAY co-locate, shared tools stay in `application/tools/` (§8.3). |
| ADR-017 | Runtime product-QA subagent + runtime kaizen loop (distinct from delivery QA/kaizen) | Playwright-MCP QA of generated carousels, **every-generation but best-effort/non-blocking** (side table, crash-safe), feeds a separate runtime-learnings loop. |
| ADR-018 | Skills layout: runtime skills **co-located in agent packages**, resolved by code; root `skills/` is delivery-only | Removes symlink intermixing; requires the skill→file dependency graph + lockstep loader/Docker/CI updates (§2.3). |
| **ADR-019** | **Tiered model selection — DeepSeek for research/scoring, Claude for voice (COMMITTED)** | Deterministic phase→model map; pilot `SourceSynthesisAgent` (research) on DeepSeek, candidate `QualityAgent` (scoring); Claude stays on content/caption/persona; pilot sourced via opencode Zen "Go", **production sourcing is an Open decision**; A/B parity vs ≥70 persona gate before committing each phase. See §13. |

---

## 11. Open decisions for the human

> **Revision 2:** several prior "open decisions" are now **resolved** (decisions.md) or **promoted to blocking ADRs** (source-of-truth → ADR-014a; per-agent scope → façade; AGENTS.md → per-agent `memory=`; runtime QA → every-generation best-effort). They are noted below as resolved. The genuinely still-open item is **production DeepSeek sourcing**.

1. **[OPEN] Production DeepSeek sourcing (ADR-019).** Pilot/dev uses the **opencode Zen "Go"** gateway (`https://opencode.ai/zen/go/v1`, `deepseek-v4-flash`/`-pro`) — the user has this subscription. **Production sourcing is undecided:** opencode Zen (pending a **ToS / SLA / data-residency** review) **vs** direct DeepSeek API (`https://api.deepseek.com`). Decide before promoting the pilot to prod. Either way, **MUST integration-test JSON/structured-output + tool-calling through the chosen endpoint** — `source_synthesis_agent.py:55-68` hard-fails `ERR_INVALID_JSON` with no graceful degrade.
2. **[OPEN] `/carousel-pipeline` as a human slash command?** Confirm whether any human/slash-command entrypoint references the runtime skills before relocating (decisions.md #2); if yes, keep a shim or update the command registration.
3. *(RESOLVED → ADR-014a, blocking)* Canonical persistence for chat Deep Agents — checkpoint vs `message_repository`. Now a **BLOCKER** that must be accepted before the harness (P3); checkpointer **replaces** the repo write or a **one-way sync** — never dual-write. See §5.3.
4. *(RESOLVED — decisions.md #3)* `AGENTS.md` → **wire as a per-agent `memory=` file** in the new package layout (registry-loadable `.md` under each agent's `prompts/`), deduped vs the system prompt.
5. *(RESOLVED — decisions.md #2)* Skills relocation → **co-locate** in agent packages (higher-touch); gated on the §2.3 dependency-graph precondition + lockstep Docker/CI updates.
6. *(RESOLVED — decisions.md #4)* Runtime QA → **every generation, best-effort/non-blocking** (§7.3): side-table report, crash-safe, revisit sampled cadence after a baseline week.
7. *(RESOLVED — decisions.md #1)* Per-agent package scope → **strict façade** (orchestration + prompts + skills + thin tool adapters; no infra moves); formalized as the §8.3 skill/tool contract.
8. *(RESOLVED by Revision 2 fact-check)* Persona/quality prompt consolidation → `TEMPLATE_ENFORCE` is **dead (no importer) → deleted**; `persona/v1/enforce.yaml` is sourced **only** from the live `_build_style_guide`. No merge of two live prompts.

---

## 12. Skeptical self-check (where this could be wrong / over-engineered)

> **Revision 2 — residual risks after the BLOCK mitigations.** The five BLOCK findings are now mitigated in-plan: (1) current-state facts corrected (20-file `skills/runtime/`, stateful chat agents, 4+1 prompts, empty orphan dir); (2) source-of-truth promoted to a blocking ADR gating P3 (no dual-write); (3) P2 gated on a skill→file dependency graph; (4) formal skill/tool contract; (5) runtime QA best-effort/non-blocking. The residual risks below remain.

- **Source-of-truth ADR could stall P3.** Making P3 hard-gated on ADR-014a is correct (dual-write is the AE-0163 trap) but means the harness can't ship until that decision lands. Mitigation: the harness's *non-chat* pieces (relocating `_build_checkpointer`, interrupt helpers, carousel-engine consumption) are **unblocked** — only the chat-agent checkpointer wiring waits. Split P3 so the unblocked work isn't held hostage.
- **`create_deep_agent` may not accept `checkpointer=`.** The plan now mandates a build-time check; if it fails, fall back to compiling the underlying graph with `.compile(checkpointer=…)` (as the carousel engine already does). Don't discover this at runtime.
- **Co-located skills move is the highest-risk physical change.** A wrong move = prod `FileNotFoundError` on auto-deploy. The §2.3 dependency-graph precondition + Docker-image path-resolution verification are the guard; do not skip them under time pressure.
- **Harness may be premature for 2 agents.** A full `harness/` package (8 modules) for two Deep Agents + one carousel graph risks gold-plating. Counter: checkpointer is *already* centralized; the harness mostly *relocates* + adds 2 presets (summarization, store). Keep it minimal — resist building `agent_factory`/`BootstrapHarness` abstractions nobody consumes yet.
- **Subagent taxonomy vs ADR-007's "deterministic nodes."** ADR-007 deliberately made phases *deterministic LangGraph nodes*, not autonomous subagents. Converting them to `task`-delegated subagents could regress the determinism/HITL guarantees. **Mitigation:** only `researcher` (needs URL nav) and `qa_reviewer` (qualitative) become true subagents; the rest stay nodes. Don't over-agentify.
- **Checkpointer for chat may add more state-sync bugs than it solves.** The chat agents are **already stateful** via `message_repository` (corrected) — manual history replay is simple and auditable. If long-context isn't a real pain yet, just add `SummarizationMiddleware` and **skip the chat checkpointer entirely**, sidestepping the source-of-truth ADR (ADR-014a) for now. Adding a second write path must clear a real need, not just "the harness supports it."
- **Prompt extraction parity risk.** Moving f-string prompts to Jinja2 YAML can silently change whitespace/ordering → drift in model output. Mandate **golden-output parity tests** (render == old f-string) before/after, or it's a behavior change masquerading as a refactor.
- **Removing root symlinks could break a human's `/carousel-pipeline` muscle memory** (memory: slash-command registration needs a symlink). Verify before P2.
- **`runtime-learnings-log.jsonl` may never accumulate enough signal** to justify a second kaizen channel for a single-user product. Could start as a manual review of QA reports; formalize the loop only if volume warrants.
- **AGENTS.md promotion could double-instruct** the model (system prompt + memory file overlap) → token waste + contradictory steering. Dedupe is mandatory if promoted.
- **DeepSeek voice/quality regression** if it creeps onto content/caption/persona phases (voice-match <70 fails the persona gate = product failure). Mitigation: hard architectural boundary — DeepSeek confined to research/scoring by *where it is injected*; the A/B parity check vs the ≥70 gate must precede committing each phase (§13).
- **DeepSeek endpoint structured-output fidelity** through the chosen gateway is unverified (`source_synthesis_agent.py:55-68` hard-fails `ERR_INVALID_JSON`). The mandated integration test for JSON/tool-calling through the endpoint is the guard; do not commit a phase to DeepSeek without it.
- **opencode Zen gateway for production is a governance unknown** (ToS/SLA/data-residency for routing user content through a third-party gateway) — kept as an explicit Open decision (#1), not silently mandated.

---

## 13. Tiered model selection — DeepSeek (COMMITTED via ADR-019)

> **Revision 2:** DeepSeek is a **committed, first-class part of this plan** — not optional, not deferred. The user explicitly wants it retained. It lands as **ADR-019** (proposed → accepted with the pilot), sequenced **after P1** (so we don't bake a cheap model onto a hardcoded prompt) and wired through the **P3 harness config** (`harness/config.py` `DeepAgentConfig` carries a per-role model map). The carousel exposes exactly one model seam (`carousel_editorial_orchestrator.py:42-52` ← `container.llm_service().chat_model`), so per-phase selection is additive wiring, not a rewrite.

### 13.1 Corrected execution detail

- **Deterministic phase→model map, chosen BEFORE invocation** — a static map (phase → primary model) resolved at orchestrator construction. **Do NOT use `.with_fallbacks([claude])` as the tier boundary.** A silent fallback makes cost + quality **unmonitorable** (you pay DeepSeek *and* Claude on every degradation) and yields a **circular quality signal** (Claude grading Claude). A separate **explicit error/escalation path** on DeepSeek failure is fine — but it is logged and counted, not the invisible tier mechanism.
- **Langfuse tagging:** every call tagged with `model_provider` and a **primary/fallback** flag, so cost attribution and the actual fallback rate are observable. A high fallback rate means DeepSeek isn't earning its place.
- **A/B quality-parity check vs the ≥70 persona gate MUST precede committing each phase.** Before a phase is switched to DeepSeek in prod, run a documented A/B comparing DeepSeek vs Claude output on that phase against the persona/quality bar; commit only if parity holds.

### 13.2 Phase placement (which phases get DeepSeek)

| Phase / agent | Model | Status |
|---|---|---|
| `SourceSynthesisAgent` (research/extraction) | **DeepSeek** | **COMMITTED pilot** (token-heavy, low-voice; "Research / Data extraction" tier) |
| `QualityAgent` (rubric/scoring) | **DeepSeek** | **Candidate** — pilot after P1 fixes its hardcoded prompt (don't bake a cheap model onto an off-registry prompt) |
| `ContentDraftAgent` (slide copy) | **Claude Sonnet** | **KEEP** — voice surface |
| caption / LinkedIn export | **Claude Sonnet** | **KEEP** — voice + platform rules |
| Persona enforce + persona **gate** | **Claude Sonnet** | **KEEP** — never offload the thing that guards voice |

> Pin `deepseek-chat`-class models (the reasoner has **no** tool-calling/structured-output). The recommended carousel phases parse JSON via prompt + `extract_json` (no `bind_tools`/`with_structured_output`), which lowers tool-calling risk but raises JSON-parse-failure surface → integration-test it.

### 13.3 Endpoint sourcing

- **Pilot / dev (KEEP):** opencode **Zen "Go"** gateway — `https://opencode.ai/zen/go/v1`, models `deepseek-v4-flash` (research) / `deepseek-v4-pro` (scoring), driven via `ChatOpenAI(base_url=…)` (the user holds this subscription). Langfuse tracing is unaffected.
- **Production sourcing = OPEN DECISION** (Open-decision #1): opencode Zen (pending a **ToS / SLA / data-residency** review for routing user content through a third-party gateway) **vs** direct DeepSeek API (`https://api.deepseek.com`). Do **not** mandate one here.
- **MUST integration-test** JSON/structured-output **and** tool-calling through whichever endpoint is chosen — `source_synthesis_agent.py:55-68` hard-fails `ERR_INVALID_JSON` with no graceful degrade. (Model IDs `deepseek-v4-*` are post-cutoff; re-confirm at implementation.)

---

## Sources (capability research)

- DeepAgents repo — *batteries-included agent harness* (subagents w/ isolated context, filesystem/HITL/summarization middleware, checkpointing): https://github.com/langchain-ai/deepagents
- DeepAgents overview docs — `create_deep_agent` kwargs (`subagents`, `middleware`, `checkpointer`, `store`, `memory`/AGENTS.md, `interrupt_on`, `permissions`); `task` tool; `general-purpose` subagent; `StateBackend`/`StoreBackend`/`CompositeBackend`: https://docs.langchain.com/oss/python/deepagents/overview
- DeepWiki `create_deep_agent` (subagent dict fields `name/description/prompt/tools/model/middleware`): https://deepwiki.com/langchain-ai/deepagents/5.1-create_deep_agent
- LangChain middleware docs — `AgentMiddleware` (`before_model`/`after_model`/`modify_model_request`), `SummarizationMiddleware`, `HumanInTheLoopMiddleware` (`interrupt_on`): https://docs.langchain.com/oss/python/langchain/middleware
- Local pins: `backend/uv.lock` → `deepagents>=0.5.3`, `langgraph==1.2.5`.
```
