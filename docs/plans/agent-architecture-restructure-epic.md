# Epic — Backend Agent-Layer Restructure (harness, façade packages, tiered models)

Status: Proposed (planner breakdown) · Tier: T3 epic · Created: 2026-06-18
Source plan: `.agent/reports/agent-architecture-restructure.arch-plan.md` (Revision 2)
Decisions: `.agent/reports/agent-architecture-restructure.decisions.md`
Skeptical corrections (code-verified, authoritative): `.agent/reports/agent-architecture.skeptical-corrections.md`
DeepSeek: `.agent/reports/carousel-deepseek-feasibility.md`, `…/opencode-deepseek-endpoint-research.md`

> Ticket IDs below are **provisional** (shown as RES-n). At emission, `ticket-writer-skill`
> allocates real `AE-####` IDs off a base that already holds the latest IDs (currently
> ≥ AE-0241) — see AE-0238 (allocator) for why. Do not pre-reserve numbers.

## Epic summary
Consolidate the backend AI-agent layer: bring all prompts under the registry, relocate
runtime skills into per-agent **façade** packages, extract a reusable Deep Agents
**harness** (checkpointer/store/memory/middleware), formalize a **subagent taxonomy**,
add **tiered model selection** (DeepSeek for cheap phases, Claude for the voice surface),
and a **best-effort runtime QA + kaizen** loop. Direction validated by the architect;
execution **BLOCKED-then-corrected** by an external skeptical pass (2 false premises
caught: `skills/runtime` is not empty; chat agents already persist to Postgres → a
checkpointer would dual-write, the AE-0163 class).

## Impact surfaces
Backend (agents/, application/, bootstrap/) · Prompts (registry) · Skills (skills/runtime → packages) · Tests (unit + rule-fires + integration) · Docs/ADRs · Deployment (Dockerfile skill paths, CI skill-path gate) · Observability (Langfuse model tags). No frontend. DB: only if the source-of-truth ADR changes the persistence path.

---

## Phase 0 — Decisions / ADRs (architect; gate the build)
- **RES-1 [T2] ADR: chat-persistence source-of-truth (BLOCKER).** Decide LangGraph
  checkpoint vs `message_repository` canonical; the checkpointer must **replace**
  message-repo persistence (or a documented one-way sync) — never dual-write (AE-0163).
  Includes a build-time check that `deepagents.create_deep_agent` (graph.py:218) accepts
  `checkpointer=`. **Blocks Phase 3.**
- **RES-2 [T2] ADR-019: tiered model selection (DeepSeek).** Deterministic phase→model
  map (NOT `.with_fallbacks` as the tier boundary); Langfuse primary/model tags; A/B
  parity vs the ≥70 persona gate before committing a phase. **Blocks RES-9.**
- **RES-3 [T2] ADRs: harness + façade + runtime-QA** (the architect's 013–018 set) —
  shape the package layout, the skill/tool contract, and the runtime kaizen channel.

## Phase 1 — Prompt consolidation (low-risk, no ADR; do first)
- **RES-4 [T1] Delete dead `TEMPLATE_ENFORCE`** (`agents/constants.py:39`, no importer).
- **RES-5 [T2] Migrate the 4 active hardcoded prompts to the registry** —
  `linkedin_post_generator.py:148`, `persona_agent.py:88` (`_build_style_guide`, parameterized),
  `quality_agent.py:53` & `:141` (quality agent → 0% off-registry). Behavior-preserving.
- **RES-6 [T1] Anti-hardcoded-prompt checker + rule-fires test** (AE-0180 standard: prove it
  FIRES on a seeded inline prompt). Wire into gates.

## Phase 2 — Skills relocation (co-locate into agent packages)
- **RES-7 [T1] Precondition: skill→file dependency-graph audit.** Map `_shared/`
  cross-refs (20 files) + all load paths (`phase_subagents.py`, `instruction_context_loader.py`,
  `domain/constants/runtime_skills.py`, Dockerfile `/app/skills/runtime`, CI skill-path gate);
  confirm repo-root symlinks are prod-dead. **Blocks RES-8.**
- **RES-8 [T2] Co-locate runtime skills** into `carousel_agent/skills/…`,
  `alter_ego_agent/skills/knowledge-base/…`; update every load path + Dockerfile + CI gate;
  drop the dead root symlinks + empty `skills/runtime/`. Verify image builds + CI skill gate.

## Phase 3 — Deep Agents harness (GATED on RES-1)
- **RES-9a [T2] Implement the source-of-truth resolution** (checkpointer replaces / one-way
  syncs message-repo) per RES-1. **Blocked by RES-1.**
- **RES-9 [T3] Extract `agents/harness/`** — shared checkpointer + store + memory +
  middleware (summarization/HITL); both agents adopt it. **Blocked by RES-9a.**

## Phase 4 — Subagent taxonomy
- **RES-10 [T2] Subagent taxonomy + URL-navigation researcher** — isolated-context jobs;
  wrap the existing `PlaywrightResearchTool` as a LangChain `@tool` on a `researcher` subagent;
  keep deterministic phases as LangGraph nodes (ADR-007). Depends on RES-9.

## Phase 5 — Per-agent façade packages
- **RES-11 [T3] Façade packages** `alter_ego_agent/`, `carousel_agent/`, `shared/` +
  **per-agent wired `memory=`** (the AGENTS.md pattern, registry-loadable) + the **skill/tool
  contract** (skill = content in package; tool = `@tool` adapter → `application/` service via
  Protocol; single-agent adapters MAY co-locate). Depends on RES-9, RES-10, RES-3.

## Phase 6 — Runtime QA + kaizen loop
- **RES-12 [T2] Runtime `qa_reviewer` subagent** — Playwright, **best-effort/non-blocking**,
  report to a side table, crash-safe (never fails the user's generation); runs every
  generation, revisit sampling after a baseline week. Feeds a **runtime kaizen** learnings
  channel parallel to the delivery loop. Depends on RES-10/RES-11.

## DeepSeek pilot (after Phase 1; uses RES-2)
- **RES-13 [T2] DeepSeek tiered-model pilot on `SourceSynthesisAgent`** (candidate
  `QualityAgent`); Claude stays on content/caption/persona. Deterministic phase→model map +
  Langfuse tags + A/B parity vs ≥70 gate. **Sourcing:** opencode Zen "Go"
  (`https://opencode.ai/zen/go/v1`, `deepseek-v4-flash/-pro`) for the pilot; **production
  sourcing = OPEN decision** (Zen pending ToS/SLA/residency vs direct `api.deepseek.com`).
  MUST integration-test JSON/structured-output + tool-calling through the endpoint
  (`source_synthesis_agent.py:55-68` hard-fails ERR_INVALID_JSON). Blocked by RES-2, RES-5.

---

## Suggested order
`RES-1, RES-2, RES-3` (ADRs) → `RES-4, RES-5, RES-6` (P1 prompts) + `RES-7` (audit) in
parallel → `RES-13` (DeepSeek pilot) + `RES-8` (skills move) → `RES-9a → RES-9` (harness)
→ `RES-10` → `RES-11` → `RES-12`.

## Risks
- **Merging `main` auto-deploys prod (~12-min blip).** Land each ticket on its own PR;
  never merge mid-incident. RES-8 especially (skill-path break = prod FileNotFoundError).
- **Dual-write (AE-0163 class)** if RES-9 lands before RES-1 is accepted — hard gate.
- **DeepSeek JSON/tool-calling** weaker than Claude → RES-13 must integration-test or the
  synthesis phase becomes fragile. **Voice regression** if DeepSeek leaks onto the voice
  surface → enforce by injection point + A/B parity gate.
- **opencode Zen** ToS/SLA/data-residency unreviewed for production user content.
- **Playwright** crashes on the droplet → RES-12 must be non-blocking (precedent: InMemorySaver fallback).
- **Façade vs Clean Arch** — RES-11 must honor the skill/tool contract or it re-creates the split-brain ADR-009 avoided.

## Handoff
→ `/architect-skill` for RES-1/RES-2/RES-3 (the ADRs that gate everything; RES-1 is the
hard blocker), then `/ticket-writer-skill` to emit Phase-1 + RES-7 + RES-13 first.
