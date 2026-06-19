I'll begin by verifying the current-state claims against live code before producing the review. Let me read the key files referenced in the packet.
Now let me check a few more things to finalize the review.
Now I have sufficient evidence to produce the review. Let me also quickly check the checkpointer wiring and the AE-0163 incident reference.
I now have enough facts verified against live code. Here is the review.

---

# Cold Critic Review

## Verdict — BLOCK

Too many unverified factual premises, unresolved architectural contradictions, and insufficient risk analysis for a green-light — especially given the production auto-deploy posture (CLAUDE.md root: pushing `main` = prod deploy).

---

## Findings

### [BLOCKER] A6 is provably false — `skills/runtime/` is NOT empty, and that changes migration scope

- **Claim contradicted by live code.** The packet states `skills/runtime/` is "an empty container". The actual filesystem shows 20 files across three populated directories (`carousel-pipeline/`, `carousel-refinement/`, `knowledge-base/`), containing phase skill markdowns, shared standards, contracts, BMaD manifests, and workflow docs. Dockerfile line 85 copies this to `/app/skills/runtime/`. The env var `ALTER_EGO_RUNTIME_SKILLS_ROOT=/app/skills/runtime` is set at production image build time (Dockerfile line 42).
- **Risk / Impact:** B3 proposes physically relocating these folders into agent packages. If the author is working from a stale mental model where `skills/runtime/` is empty, the relocation plan is blind to the actual file count, dependencies, and shared-standard cross-references (six `_shared/` files referenced by `phase_subagents.py:27-62`). The migration will uncover hidden coupling mid-flight.
- **Suggested mitigation:** Before any P2 work, audit every file in `skills/runtime/carousel-pipeline/_shared/` for cross-references from other skill directories (`skills/runtime/carousel-refinement/SKILL.md` and `knowledge-base/SKILL.md` may also reference these). Produce a dependency graph of skill→shared-file edges. Then decide whether to copy, symlink, or share a common `_shared/`.
- **Open question:** Are the repo-root symlinks (`skills/carousel-pipeline → runtime/carousel-pipeline`) consumed by ANY production code path or only by the CLI/developer workflow? The code resolves via `get_runtime_skills_filesystem_root()`, which returns `skills/runtime/` — not the symlinks. If the symlinks are unused in production, they are dead noise and should not influence the physical-layout decision.

### [BLOCKER] B2+B3: FAÇADE-vs-co-locate creates a boundary leak that Clean Architecture cannot enforce

- **Assumption challenged:** B2 says "business-logic tools/services STAY in `application/` (to preserve Clean Arch / ADR-009)". B3 says "physically CO-LOCATE the runtime skill folders into their agent package." The packet treats these as complementary. They are not.
- **Why this fails:** A carousel-phase subagent (e.g., `content_drafter`) loads its skill markdown via `instruction_context_loader.py:101-126` which calls `phase_subagents.py:27-62` to resolve `SKILL_ROOT + "/phases/content"`. That skill markdown describes the subagent's task — but the subagent also uses tool functions registered in `rag_backend.application.tools.carousel.*`. The agent's **behavior** is thus split across two physical locations (`carousel_agent/skills/` for prompt/identity, `application/tools/` for executable logic), while the **test fixture** and **loader path** must span both. A developer debugging a content-draft failure has to context-switch between two trees.
- **Impact:** This creates exactly the "confusing split-brain" the reviewer's challenge question identified. The project's ADR-009 domain modular monolith was adopted precisely to avoid this kind of artifact scattering. If the agent owns its skills (prompts, subagent definitions), it should also own its tools — or the distinction between "skill" (what the agent reads) and "tool" (what it calls) needs a formal contract, not a location convention.
- **Suggested mitigation:** Adopt a stricter rule: an agent package contains everything the agent needs to be instantiated — prompts, subagent definitions, skill markdowns, AND the `@tool` functions. The `application/tools/` directory should contain only tools shared across MULTIPLE agents. If a tool is consumed by exactly one agent, move it into the agent package. This is testable: `git diff` on any agent package should reveal whether it imports from outside its boundary.
- **Open question:** Would the project accept a per-agent `tools/` subdirectory (e.g., `carousel_agent/tools/content_draft_tool.py`) that duplicates the LangChain `@tool` wrapping but delegates to an `application/` service for business logic? Or should the delegation be inverted — `application/services/` exposes a Protocol, and the agent's tool is the adapter?

### [WARN] A2 mischaracterizes the RAG agent's statefulness, weakening the case for a checkpointer

- **Claim vs reality:** The packet says both Deep Agents run "effectively STATELESS (no chat persistence)." In reality, both `RAGAgent` and `AlterEgoAgent` persist every user and assistant message to the Postgres `message_repository` (`rag_agent.py:192-198, 270-277`; `alter_ego_agent.py:141-147, 217-223`). They rebuild history from the DB on every invocation (`rag_agent.py:181-190`; `alter_ego_agent.py:130-138`). They lack a LangGraph checkpointer, but they DO have durable chat persistence.
- **Impact:** B1 proposes giving the chat agent a checkpointer under the banner "today stateless". This frames the checkpointer as net-new capability. In reality, it introduces a **second persistence path** alongside the existing message_repository — a dual-write. The AE-0163 precedent shows the project has already suffered data-loss from dual-write patterns (`carousel_blog_dual_write.py`, `distribution_home.py`). Adding a checkpointer without resolving B8 first is cargo-culting the exact bug class that caused AE-0163.
- **Suggested mitigation:** The checkpointer should replace the message_repository persistence, not add to it. Either: (a) make the checkpointer the sole source of conversation history and remove the explicit `message_repository.create()` calls in the chat methods, or (b) formally adopt the queue-in-the-middle pattern — write only to the checkpointer, have a background consumer sync to the message_repository for audit — and document which is canonical. Anything else repeats AE-0163.
- **Open question:** Can `create_deep_agent()` from the DeepAgents library even accept a LangGraph checkpointer? The deepagents library's `create_deep_agent()` interface (`rag_agent.py:103-109`, `alter_ego_agent.py:90-96`) does not expose a `checkpointer=` parameter. What's the migration path if the library doesn't support it?

### [WARN] C1 boundary integrity by "injection point" is not analyzable without model fallback semantics

- **Assumption challenged:** C1 says the boundary between DeepSeek phases and Claude phases is "enforced by which model is injected where." The fallback chain `ChatOpenAI(...).with_fallbacks([claude_sonnet])` (C2) subverts this entirely. If the Zen gateway returns a 503 or a silent empty response, the fallback fires and Claude handles the DeepSeek-intended phase anyway — but the user is NOT billed for DeepSeek, and the latency profile is unpredictable (DeepSeek timeout + Claude fallback).
- **Impact:** Two failure modes: (1) **Silent cost escalation** — the fallback to Claude on every "cheap" phase when Zen is degraded makes your cost higher than all-Claude (you pay for the failed DeepSeek call AND the Claude fallback). (2) **Unpredictable quality** — the persona gate (`≥70 voice match`) runs on Claude regardless (C1 says "ALL persona enforce/gate scoring uses Claude"), but if Claude is handling a slide draft via fallback, the content it score-checks was already generated by Claude, not DeepSeek. The quality measurement is circular — Claude grades Claude, and you learn nothing about whether DeepSeek would have passed the gate.
- **Suggested mitigation:** Do not use `.with_fallbacks()` for model-tier boundaries. Instead, use a deterministic phase-model map that selects the model BEFORE invocation and logs which model was chosen. If DeepSeek fails, surface a retry-or-escalate event rather than silently falling back to Claude. Then A/B test the quality parity per phase before committing.
- **Open question:** What is the actual cost delta? The packet assumes DeepSeek v4 is cheaper. But `deepseek-v4-pro` through a third-party gateway may carry margin. Has the author fetched per-token pricing for the Zen gateway to confirm it beats Claude Sonnet at the volumes the carousel pipeline runs (say 50-100 generations/day)?

### [WARN] C2: routing User Content through `opencode.ai/zen/go/v1` is an un-reviewed data-residency and ToS gamble

- **Risk:** The Zen gateway is an open-source hobby project gateway. Its ToS, data-retention policy, sub-processing agreements, and SLA are not documented in the packet. The carousel pipeline generates text about the user's personal brand, blog posts, and potentially draft paid content. Routing this through an un-audited third party whose sole public interface is `opencode.ai/zen/go/v1` creates a supply-chain trust issue.
- **Impact:** In a production deployment (auto-deploy to DO droplet), this becomes a data-residency liability. Even if DeepSeek via Azure or direct API is acceptable, the Zen gateway adds an opaque intermediary that could log, cache, or redirect traffic. The project's existing compliance posture (no secrets in code, Dependabot, etc.) has no policy for this.
- **Suggested mitigation:** Default to **direct DeepSeek API** (`api.deepseek.com`) or DeepSeek via a major cloud marketplace (AWS Bedrock, GCP Vertex AI) for any production use. The Zen gateway path is acceptable ONLY for local development A/B testing behind `ALTER_EGO_ENV=dev`, gated by a settings override that defaults to the direct API. Add a `data_residency` check to `startup_validation.py`.
- **Open question:** Has the packet author confirmed that the Zen gateway produces valid JSON structured outputs and that tool-calling (`@tool` with the researcher subagent) round-trips correctly? DeepSeek models historically have weaker structured-output compliance than Claude Sonnet. If JSON-mode fails for the `SourceSynthesisAgent` output, the `extract_json` fallback in `source_synthesis_agent.py:55-68` already has a `try/except` for `json.JSONDecodeError`, but it hard-fails with `ERR_INVALID_JSON` — it does not degrade gracefully.

### [WARN] B6: "Playwright QA on EVERY generation" — cost, flakiness, and failure-isolation are unaddressed

- **Assumption challenged:** The packet proposes a `qa_reviewer` subagent using Playwright on every carousel generation. Playwright is already in the image (Dockerfile line 74), and a `PlaywrightResearchTool` exists in the container (`container.py:158`). But Playwright is a heavy, stateful dependency — it launches a full headless Chromium process. Running it on every generation multiplies latency.
- **Risk / Impact:** The current carousel pipeline already has 7 phases (P1-P7) with human `interrupt()` gates. Adding a Playwright-based QA reviewer that scrapes/stages the carousel and produces a quality report adds at least 5-15 seconds per generation (Chromium cold-start + page render + report API). For a batch of 1 carousel, this may be acceptable. For a campaign of 10+, this becomes a scaling bottleneck. Worse, if Playwright crashes (as it does on resource-constrained droplets — see existing fallback to `InMemorySaver` in `app_factory.py:167-171` for a similar backstop pattern), the entire generation job fails unless the QA step is made **best-effort** and non-fatal.
- **Suggested mitigation:** Make the `qa_reviewer` subagent a **non-blocking side-effect** that writes its report to a separate `quality_logs` table and does not gate the user's result. If it crashes or times out, the generation proceeds. Then run it at **sampled** frequency (every 5th generation for human-review pass, every 1st for the first week of deployment to establish a baseline). This avoids the "what happens to the user's result if QA hangs/crashes?" problem.
- **Open question:** What does "produces a quality report" actually mean — screenshot diffing? DOM tree analysis? Semantic scoring via another LLM call? If the latter, the `qa_reviewer` subagent itself needs an LLM invocation, which doubles the per-generation cost. This is not scoped in the packet.

### [INFO] A4 is self-contradicting — `agents/carousel_orchestrator/` does not exist even as stale .pyc

- **Factual correction:** The packet claims "only stale `.pyc`; source removed per ADR-007." The filesystem shows the directory does not exist — no `.pyc` files, no directory entry. The carousel orchestration code now lives in `agents/carousel_editorial_orchestrator.py` and `agents/carousel_workflow_engine.py`. The removal is complete. This does not change the migration plan but removing stale claims from the factual foundation would improve trust in the analysis.
- **Impact:** Low. The packet overstates the cleanup work remaining.

### [INFO] A5: One of the 5 claimed hardcoded prompts is dead code

- **Factual correction:** `TEMPLATE_ENFORCE` in `agents/constants.py:39-79` is defined but imported by ZERO modules (`grep` confirms only the definition site). It is dead code. The remaining 4 are active:
  1. `linkedin_post_generator.py:148-169` — hardcoded LinkedIn prompt
  2. `persona_agent.py:88-108` (`_build_style_guide`) — structurally hardcoded prompt template that interpolates persona data (arguably a "template" not a "hardcoded string" but still off-registry)
  3. `quality_agent.py:53-69` (`_build_evaluation_prompt`) — hardcoded
  4. `quality_agent.py:141-149` (`generate_improvement_suggestions`) — hardcoded
- **Impact:** The P1 prompt consolidation estimate should be 4 active remediations, not 5. The `TEMPLATE_ENFORCE` can be removed or re-registered as dead weight. The `persona_agent.py:88` case is the hardest — the style guide is dynamically built from persona data; rewriting it to use the registry without losing the structure would require either Jinja2 with persona fields as variables or a new registry pattern for parameterized system prompts.

### [INFO] A3 is confirmed — AGENTS.md is a ghost file

- Zero code paths load `agents/AGENTS.md`. B4 proposes wiring it as a `memory=` file, which would be net-new behavior. This is fine, but the packet should document what the file looks like if loaded (it already contains a comprehensive system prompt) and whether it would REPLACE or augment the existing registry-loaded system prompts (`rag_agent.py:52-54` loads `get_system_prompt("rag", version="v1")` from the registry; `alter_ego_agent.py:101-103` loads `get_system_prompt("alter_ego", version="v3")`).

---

## Disproven or Unverified Claims

| Claim | Verdict | Evidence |
|-------|---------|----------|
| A6: `skills/runtime/` is "an empty container" | **DISPROVEN** | 20 files across 3 directories. `skills/runtime/carousel-pipeline/` contains 17 files including 5 phase SKILL.md, 6 shared standards, contracts, manifests. See `find skills/runtime -type f \| sort`. |
| A2: Deep Agents "run effectively STATELESS (no chat persistence)" | **DISPROVEN** (misleading) | `rag_agent.py:192-198,270-277` and `alter_ego_agent.py:141-147,217-223` persist every message to Postgres message_repository. They lack a LangGraph checkpointer but have DB-driven chat persistence. |
| A4: "only stale .pyc" from carousel_orchestrator/ | **DISPROVEN** (overstated) | Directory and .pyc do not exist. Clean removal. |
| A5: "5 hardcoded prompt violations" | **NUANCED** | `TEMPLATE_ENFORCE` (agents/constants.py:39) is dead code — defined but never imported. 4 active violations remain. |
| C2: "Langfuse callback assumed to still work" with `ChatOpenAI(base_url=..., api_key=...)` | **UNVERIFIED** | Langfuse's `CallbackHandler` wraps LangChain's `BaseCallbackHandler`. It should work with any `ChatOpenAI` instance since it's framework-level, not provider-level. But if the Zen gateway returns streaming chunks in a non-standard SSE format, the callback's `on_llm_new_token` may not fire correctly, breaking token-level tracing. This must be integration-tested, not assumed. |

---

## Missing Evidence

1. **DeepSeek structured-output test results** — `SourceSynthesisAgent` requires JSON output (`source_synthesis_agent.py:55-68`). Does DeepSeek v4 through Zen produce valid, parseable JSON 99%+ of the time? What is the malformed-JSON rate compared to Claude Sonnet? If it exceeds the current `try/except json.JSONDecodeError` tolerance, the entire source-synthesis phase becomes fragile.

2. **Zen gateway SLA / ToS / data-retention policy** — Without reviewing the opencode Zen ToS, the proposal is shipping a dependency with unknown data-handling guarantees in a production system that auto-deploys.

3. **Cost model for the DeepSeek split** — The packet proposes using DeepSeek for `SourceSynthesisAgent` and optionally `QualityAgent`. Source synthesis runs once per carousel. Quality evaluation runs per-evaluation method. What is the projected monthly cost at peak volume with all-Claude vs the split? If the savings are <$50/month, the engineering risk of maintaining two model pipelines may not be justified.

4. **DeepAgents library checkpointer support** — `create_deep_agent()` (`rag_agent.py:103`, `alter_ego_agent.py:90`) does not accept a `checkpointer=` parameter in its current call signature. B1 assumes adding a checkpointer to the chat agent is a straight-forward wiring change. If the library abstracts model invocation and does not expose LangGraph's low-level checkpointer API, B1 may require forking or patching the `deepagents` package.

5. **Migration sequence coupling analysis** — The 7-phase plan (P1-P7) assumes P1 (prompt consolidation) and P2 (skills relocation) are safe to parallelize first. But the instruction_context_loader (`instruction_context_loader.py:101-126`) links phase skills to prompt rendering via the `CAROUSEL_PROMPT_VERSION_V3` constant. If P2 moves the skill files before P1 finishes migrating the prompts that reference them, the loader path will break. Is there a formal dependency graph showing which prompts reference which skill files?

---

## Residual Risks if It Proceeds Unchanged

1. **Dual-write data loss** — Granting the chat agent a LangGraph checkpointer while the message_repository already persists messages creates two sources of truth. The AE-0163 precedent proves this codebase cannot safely manage dual-writes without prior ADR resolution. This is the single highest-severity risk in the proposal.

2. **Skills relocation breaks production on deploy** — Because `skills/runtime/` currently contains real files with real cross-references, moving them without first auditing all load paths will produce `FileNotFoundError` in production (phase_subagents loads `SKILL_ROOT + "/phases/research"` → the file must exist at exactly the resolved path). A rollback of a deployment from a broken image would require re-building, not just re-deploying the previous tag (since the image layer would be different).

3. **Model fallback leakage** — `.with_fallbacks([claude_sonnet])` on the DeepSeek `ChatOpenAI` instance creates a cost and quality unpredictability that cannot be monitored without per-invocation telemetry (which the current Langfuse setup — tracking by agent name — does not distinguish between primary vs fallback invocation). A production incident where every carousel generation silently costs 2x expected token count while QA reports "everything passed" is plausible.

4. **Uncodified source-of-truth policy** — The packet acknowledges B8 as "OPEN" but proceeds with P3 (harness) anyway. Building a harness without resolving the canonical store means the harness will be wired ad-hoc and will need to be re-architected when the ADR lands. This is building on an unresolved foundation.

5. **Playwright QA as a blocking gate** — If the runtime QA reviewer (B6) is not explicitly built as best-effort or sampled, a single Chromium crash on a headless DO droplet (which has happened before, per the InMemorySaver fallback precedent) will block an entire carousel generation from reaching the user, creating a support escalation.
