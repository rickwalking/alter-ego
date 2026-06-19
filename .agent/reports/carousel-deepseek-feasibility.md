# Carousel × DeepSeek — Feasibility Verdict (Architect, read-only)

**Mode:** architect / research+validate (no production edits)
**Date:** 2026-06-18
**Repo:** alter-ego
**Idea (user's words):** "Use opencode DeepSeek in the carousel agent."
**Knowledge-cutoff caveat:** my training cutoff is Jan 2026. DeepSeek's *current* model IDs (web search returned post-cutoff `deepseek-v4-flash`/`deepseek-v4-pro`) are **unverified by me** — treat exact IDs as "confirm at implementation time." The *architectural* facts (OpenAI-compatible API, `langchain-deepseek`/`ChatDeepSeek`, reasoner-has-no-tool-calling) are stable and load-bearing.

---

## 0. The two interpretations (the heart of it)

The phrase conflates two very different things. They must be judged separately.

| | **(1) DeepSeek-the-model via API** | **(2) opencode-the-CLI inside the runtime agent** |
|---|---|---|
| What it is | `ChatDeepSeek(...)` / `ChatOpenAI(base_url="https://api.deepseek.com", ...)` slotted into LangChain as a `BaseChatModel` | Shelling out to the `opencode` CLI (as `scripts/lib/external_agent.sh` does) from inside request-time carousel generation |
| Latency | ~API call (seconds), streamable | **minutes**; `EXTERNAL_STREAM_WAIT_SECS=90`, `EXTERNAL_RUN_TIMEOUT_SECS=1500` (`external_agent.sh:25-26`) |
| Streaming | native `.astream()` | none — buffered stdout, ANSI-stripped after the fact (`ext_strip_ansi`, `external_agent.sh:42`) |
| Tool-calling / structured output | first-class on `deepseek-chat` (V3) | none — it's a text blob; verdict scraped by regex (`run_external_qa.sh:27`) |
| LangGraph integration | drop-in `BaseChatModel` | impossible to use as a graph node model; it's a subprocess |
| Checkpointing | works (model is stateless to the graph) | N/A — runs in a **detached throwaway worktree** (`ext_run_guarded`, `external_agent.sh:109`) |
| Langfuse tracing | works via the LangChain callback (see §4) | **no trace at all** — opaque subprocess |
| Determinism / HITL `interrupt()` | unaffected (graph still owns gates) | breaks the model — opencode is an autonomous agent that picks its own steps |

**Verdict (1): CONDITIONAL — feasible and the sound reading.** This is the only interpretation that fits the carousel pipeline.
**Verdict (2): NOT-RECOMMENDED for the generation hot path.** A minutes-latency, untraceable, non-streaming subprocess cannot be a request-time content generator behind `interrupt()` HITL gates. opencode *does* have one legitimate, off-hot-path role — the runtime **QA reviewer** (§5).

> Interpretation note: "opencode DeepSeek" likely conflates two real facts — opencode *can be configured to call DeepSeek*, and the repo *already uses opencode offline*. But running opencode in-request is the wrong mechanism; if you want DeepSeek in carousel generation, call the **DeepSeek model API directly** through LangChain. Don't route it through the CLI harness.

---

## 1. How the carousel actually wires its model (evidence)

The carousel does **not** hardcode a provider in its phase agents — every phase agent takes a `BaseChatModel` by constructor injection, so swapping the model is a wiring change, not a rewrite:

- `OutlineAgent.__init__(self, llm: BaseChatModel, ...)` — `agents/outline_agent.py:35`
- `ContentDraftAgent.__init__(self, llm: BaseChatModel, ...)` — `agents/content_draft_agent.py:34`
- `SourceSynthesisAgent.__init__(self, llm: BaseChatModel, ...)` — `agents/source_synthesis_agent.py:24`
- `QualityAgent.__init__(self, ..., llm: BaseChatModel, ...)` — `agents/quality_agent.py:24`

**The single seam.** All of them are fed the *same* model today:
- `CarouselEditorialOrchestrator.__init__(self, llm: BaseChatModel, ...)` → builds `OutlineAgent(llm=llm)`, `ContentDraftAgent(llm=llm)`, `SourceSynthesisAgent(llm=llm)` — `agents/carousel_editorial_orchestrator.py:33-52`.
- That `llm` is `container.llm_service().chat_model` — `api/routes/carousels/editorial_workflow_routes_support.py:36`, `api/dependencies/agents.py:284`.
- `chat_model` is a single `ChatAnthropic` (claude-sonnet-4-6) DI **Singleton** — `infrastructure/external/anthropic_llm.py:26`, `infrastructure/container.py:112-115`, `infrastructure/config/settings.py:46`.

So there is **exactly one place** to introduce per-phase model selection: pass a *second* (cheap) `BaseChatModel` into the orchestrator and hand it only to the phases that should use it. No phase-agent code changes.

**Important nuance — these phases parse JSON manually, not via native structured output.** `OutlineAgent`/`ContentDraftAgent`/`SourceSynthesisAgent` call `self.llm.ainvoke(...)` then `extract_json(...)` (`infrastructure/llm/json_utils.py`, plus a `_JSON_REPAIR_PROMPT` fallback). They do **not** call `with_structured_output()` or `bind_tools()`. This *lowers* the DeepSeek risk for these phases (no dependence on provider-specific tool-calling fidelity) but *raises* the JSON-parse-failure surface (§3, §6).

The **DeepAgents `task` entry door** (`rag_agent.py:103-109` builds `create_deep_agent(model=self._llm, ...)`) is a *different* model — that's the conversational RAG agent that *starts* the carousel workflow. That one orchestrates tool calls and **must keep Claude** (tool-calling-heavy, voice-bearing chat). DeepSeek belongs *inside* the deterministic carousel graph's cheap phases, not as the DeepAgents orchestrator model.

---

## 2. Where a cheap model fits (map to the Model-Selection table)

CLAUDE.md's "Model Selection Strategy" is the rubric. Mapping the carousel phases (`phase_subagents.py:9-12`, and their executing agents):

| Phase / agent | CLAUDE.md category | DeepSeek? | Why |
|---|---|---|---|
| `research_synthesizer` / `SourceSynthesisAgent` (`source_synthesis_agent.py`) | Research / Data extraction | ✅ **Good candidate** | Extraction/summarization of sources → JSON. Exactly the "GPT-4o-mini" tier in the table. Cheapest win, lowest voice risk. |
| `outline_planner` / `OutlineAgent` (`outline_agent.py`) | Structuring (between research & creative) | 🟡 **Conditional** | Slide *plan* from brief+research. Structural, not yet voice-bearing → defensible on DeepSeek, but it shapes downstream copy. Pilot *after* research proves out. |
| `content_drafter` / `ContentDraftAgent` (`content_draft_agent.py`) | **Creative writing / Voice matching** | ❌ **Keep Claude Sonnet** | Writes slide copy "with persona enforcement" (`phase_subagents.py:48`). This is the voice surface. |
| `caption_writer` (final-review) | Creative / distribution voice | ❌ **Keep Claude** | IG caption + LinkedIn export copy = voice + platform rules. |
| Persona enforce (`persona_agent.py`) / persona **gate** scoring | Voice matching / persona | ❌ **Keep Claude** | `PersonaAgent.enforce()` + voice-match ≥70 gate (CLAUDE.md). Never offload the thing that *guards* voice. |
| `QualityAgent` rubric/E-E-A-T scoring (`quality_agent.py`) | **Quality scoring / Deterministic** | ✅ **Good candidate** | "GPT-4o-mini" tier in the table. Scoring → JSON. But it's an off-registry prompt-hardcoding violation (arch-plan §1, P1) — fix that first or you bake a cheap model onto a hardcoded prompt. |

**Recommendation:** start DeepSeek on **`SourceSynthesisAgent` (research) only**, optionally **`QualityAgent` (scoring)** — the two table-sanctioned "cheap-model" categories. Hold `OutlineAgent` as a *phase-2* pilot. **Never** put DeepSeek on content/caption/persona — that's the voice, and voice-match <70 fails the persona gate and the whole point of the product.

---

## 3. Tool-calling + structured-output risk

**The load-bearing fact:** `deepseek-reasoner` (R1) **does NOT support tool calling or structured output**; only `deepseek-chat` (V3) does (LangChain integration docs). So:

- If anyone wires DeepSeek as the **DeepAgents orchestrator** model (the `task`/tool-calling agent, `rag_agent.py`), and picks the reasoner, **tool dispatch silently breaks**. → **Never use `deepseek-reasoner` where `bind_tools`/`with_structured_output` is used.** Pin `deepseek-chat`.
- For the **carousel phases** I recommend (research/scoring/outline), the risk is *lower*: they don't use `bind_tools`/`with_structured_output` — they prompt for JSON and run `extract_json` + a repair prompt. So tool-calling fidelity is moot there.
- **What breaks if JSON is weaker:** DeepSeek-chat supports `response_format={'type':'json_object'}` (DeepSeek JSON-mode docs), but the carousel agents don't pass it today — they rely on prompt-instructed JSON + `extract_json`. A weaker model that emits prose-wrapped or truncated JSON → `extract_json` fails → the phase degrades. Mitigations: (a) opt these phases into DeepSeek's JSON mode, (b) keep the existing `_JSON_REPAIR_PROMPT` path, (c) **fall back to Claude on parse failure** (§6).
- **max_tokens caveat:** the Anthropic service runs `max_tokens=32000` "because bilingual PT+EN slide arrays were truncating" (`anthropic_llm.py:31-34`). A DeepSeek model used for the *bilingual content* phase would inherit that truncation risk — another reason content stays on Claude and DeepSeek is confined to single-language extraction/scoring.

---

## 4. Observability (Langfuse)

- **DeepSeek-as-model: tracing works, unchanged.** Langfuse is wired as a **LangChain callback** (`monitoring_langfuse.py` `init_langfuse` → `CallbackHandler`), injected per-call via `get_langfuse_runnable_config()` (used by `outline_agent.py:86`, `content_draft_agent.py`, `source_synthesis_agent.py:50`, `quality_agent.py:45`). The callback is provider-agnostic — any `BaseChatModel` (including `ChatDeepSeek`/`ChatOpenAI` base_url) is traced identically. Token usage/cost per phase still attributes. **No tracing regression.** (Tag the trace `metadata.model_provider="deepseek"` so cost analysis can separate it — cheap to add.)
- **opencode-CLI path: NO tracing at all.** It's an opaque subprocess; nothing flows through the LangChain callback. This violates CLAUDE.md "All LLM Calls Must Be Traced" — a hard reason interpretation (2) cannot be on the generation path.

---

## 5. Does the opencode offline harness have a legitimate place here?

**Yes — exactly one, and it's NOT generation.** It maps cleanly onto the arch-plan's **runtime `qa_reviewer`** (arch-plan §7; decisions.md item 4 — "runtime QA every generation"):

- The harness (`external_agent.sh` + `run_external_qa.sh`) is *purpose-built* for "run a prompt through an isolated, non-streaming, worktree-sandboxed external CLI and scrape a verdict." That is the shape of an **after-the-fact, async, non-blocking** QA reviewer that "must not fail the generation" (decisions.md item 4).
- It is the *wrong* shape for anything request-time/streaming/HITL.
- **But** the arch-plan's `qa_reviewer` is specified as **Playwright-MCP-driven** (visual/slide QA), not a text-CLI. So `external_agent.sh` is a *reference pattern* (worktree isolation, hang-recovery, timeout, AE-0170 guard) more than a literal reuse. If you want a *cheap text* runtime-QA pass, opencode-configured-with-DeepSeek is a legitimate offload — **but** prefer the native `ChatDeepSeek` model inside the `qa_reviewer` node over shelling to the CLI, so you keep Langfuse + determinism. Net: **the harness's place is the QA channel, off the hot path; even there, the model-API path is cleaner than the CLI path.**

---

## 6. Cost / latency / reliability trade-offs + failure modes

**Upside:** DeepSeek is materially cheaper than Sonnet per token; research/scoring are token-heavy, low-voice phases → real cost savings with low quality risk.

**Failure modes + mitigations:**
| Failure | Impact | Mitigation |
|---|---|---|
| DeepSeek API outage / 5xx | research/scoring phase fails | **Fallback model**: wrap with `.with_fallbacks([claude])` (LangChain) so a DeepSeek failure transparently retries on the existing Anthropic Singleton. Single most important mitigation. |
| Rate limits / throttling | latency spikes / 429s | `max_retries` (DeepSeek client supports it) + fallback; the phases are already async. |
| Weaker/malformed JSON | `extract_json` fails → phase degrades | DeepSeek JSON-mode + existing `_JSON_REPAIR_PROMPT` + fallback-to-Claude on parse failure. |
| Region / data-residency | DeepSeek inference is PRC-hosted; source material + briefs leave to a CN endpoint | **Governance call, not technical.** Confine DeepSeek to *non-sensitive* extraction; document in the ADR; consider per-deployment opt-out flag. This is the **policy** risk, distinct from the engineering ones. |
| `deepseek-reasoner` used with tools | silent tool-call breakage | **Pin `deepseek-chat`**; never the reasoner where tools/structured-output are used (§3). |
| Voice drift if content phase swapped | persona gate <70, product failure | **Don't** put DeepSeek on content/caption/persona (§2). |

**The single biggest risk:** not latency or cost — it's **voice/quality regression if DeepSeek creeps onto the content/caption/persona phases.** The whole product is persona-fidelity (voice-match ≥70 gate); a cheap model there fails the gate and defeats the point. The mitigation is a hard architectural boundary: DeepSeek confined to research/scoring, enforced by where it's injected.

---

## 7. Proposed ADR + phase placement

**ADR-019 — "Tiered model selection for carousel phases (DeepSeek for research/scoring, Claude for voice)"**
- *Status:* proposed.
- *Context:* carousel phases vary from token-heavy extraction (cheap-model-suitable per the Model-Selection table) to voice-bearing copy (must stay Claude). All phases currently share one Anthropic Singleton.
- *Decision:* introduce a per-phase model policy. Inject a cheap `BaseChatModel` (DeepSeek `deepseek-chat` via `langchain-deepseek`/`ChatDeepSeek`, **with a Claude fallback**) into `SourceSynthesisAgent` (and optionally `QualityAgent`); keep Claude Sonnet for `ContentDraftAgent`, caption, and all persona enforcement/gates. **Never** use `deepseek-reasoner` where tool-calling/structured-output is required. Add `deepseek_*` settings (api_key as `SecretStr`, model, base_url) to `Settings`; a second DI provider; trace tag `model_provider`.
- *Consequences:* cost ↓ on research/scoring; new external dependency + region/residency governance; one new seam (orchestrator takes `research_llm` alongside `llm`).
- *Rejected alternative:* opencode-CLI-in-request (no streaming, no tracing, minutes latency, breaks HITL — §0).

**Where it lands in the 7-phase migration (arch-plan §9):** **after P1 (prompt consolidation)** and ideally **alongside/after P3 (harness)**. Rationale: (a) P1 moves `quality_agent`'s hardcoded prompt into the registry — do that *before* attaching a cheap model to scoring, or you bake DeepSeek onto a hardcoded prompt; (b) the P3 harness is the natural home for a **model-selection/policy** concern (`harness/config.py` `DeepAgentConfig` already carries `model`) — extend it to a per-role model map rather than scattering `if deepseek` across phases. This is an **independent, additive** workstream (new ADR-019) that slots between P1 and P3; it does not block the restructure. Tier: **T2** (additive wiring + settings + fallback + parity tests; no graph-topology change).

---

## 8. Skeptical self-check (where this could be wrong / over-engineered)

- **Model IDs are post-cutoff.** I could not verify `deepseek-v4-*` vs `deepseek-chat`/`deepseek-reasoner`. The *architecture* (inject a cheap `BaseChatModel` with a Claude fallback) is ID-agnostic; confirm the live ID + that it supports JSON before shipping. The **reasoner-has-no-tool-calling** constraint is the one fact that must be re-checked against whatever ID is chosen.
- **Savings may be marginal for a single-user product.** If carousel volume is low, the per-month $ saved may not justify a new external dependency + a CN-residency governance review. Counter: research/scoring are the token-heaviest phases, and the wiring is small (one seam) — but *measure expected volume* before committing. Could be premature optimization.
- **`.with_fallbacks` hides quality regressions.** A silent fallback-to-Claude masks DeepSeek failing often → you pay for DeepSeek *and* Claude and think DeepSeek "works." Mitigation: count fallbacks in Langfuse; if the fallback rate is high, DeepSeek isn't earning its place.
- **JSON-mode assumption.** I'm inferring the phases would benefit from DeepSeek JSON mode; they currently rely on prompt+`extract_json`. Verify `extract_json` tolerates DeepSeek output shape with a golden-output test before trusting it in prod.
- **opencode-as-QA could be over-engineering.** The arch-plan already specifies a Playwright-MCP `qa_reviewer`; bolting a *second* (text, opencode-DeepSeek) QA path risks two competing QA channels. Prefer one. opencode's value here is the *isolation/hang-recovery pattern*, not a mandate to run it.
- **The user said "opencode DeepSeek" explicitly.** I'm overriding the literal CLI reading in favor of the model-API reading. If the user genuinely wants the *CLI* (e.g. to avoid an API key, reuse an opencode subscription), that's a deliberate trade — but it's incompatible with streaming/HITL/tracing on the generation path, so it can only live in the off-hot-path QA channel.

---

## Sources

- DeepSeek API — OpenAI-compatible base_url, models: https://api-docs.deepseek.com/
- DeepSeek Function Calling: https://api-docs.deepseek.com/guides/function_calling
- DeepSeek JSON mode (`response_format`): https://api-docs.deepseek.com/guides/json_mode
- LangChain `ChatDeepSeek` integration (reasoner has **no** tool-calling/structured-output; use `deepseek-chat`): https://docs.langchain.com/oss/python/integrations/chat/deepseek
- `ChatDeepSeek` reference: https://reference.langchain.com/python/langchain-deepseek/chat_models/ChatDeepSeek
- Local code: `infrastructure/external/anthropic_llm.py:26`, `infrastructure/container.py:112`, `agents/carousel_editorial_orchestrator.py:33-52`, `agents/outline_agent.py:35`, `agents/source_synthesis_agent.py:24`, `agents/quality_agent.py:24`, `scripts/lib/external_agent.sh:25-158`, `scripts/qa/run_external_qa.sh:27`.
