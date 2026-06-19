# Architecture plan — skeptical-review corrections (2026-06-18)

External opencode cold-critic verdict: **BLOCK**. Full review:
`.agent/reports/agent-architecture.skeptical-review.md`. Findings re-verified against live
code (the critic is advisory, not authoritative — but here it was RIGHT on the disputed facts).
**The restructure plan must be revised on these points BEFORE any ticket emission.**

## Disproven premises (verified against live code — my architect agents were wrong)

| Premise (in arch-plan) | Verdict | Live-code evidence | Consequence |
|---|---|---|---|
| `skills/runtime/` is "an empty container" (A6) | **FALSE** | `find skills/runtime -type f` = **20 files**; carousel-pipeline has 5 phase SKILL.md + 6 `_shared/*.md` + contracts/manifest | P2 skills relocation is bigger + has `_shared` cross-reference coupling. Co-locate (decision 2) needs a **skill→shared-file dependency audit first**. |
| Both Deep Agents "run effectively STATELESS" (A2) | **FALSE** | `rag_agent.py:198,277,315` + `alter_ego_agent.py:147,223,261` `message_repository.create(...)`; history rebuilt from DB (`:181`/`:130`) | Chat agents ALREADY persist to Postgres. A LangGraph checkpointer (B1) = **second write path = AE-0163 dual-write class.** |
| "5 hardcoded prompts" (A5) | **NUANCED** | `TEMPLATE_ENFORCE` (constants.py:39) has **no importer** → dead code | **4 active** remediations + delete the dead one. |
| carousel_orchestrator "only stale .pyc" (A4) | overstated | dir exists but empty (no source) | cosmetic; removal is clean. |
| AGENTS.md unused (A3) | **CONFIRMED** | no loader | B4 (wire as memory) is net-new; decide replace-vs-augment the registry `get_system_prompt("rag"/"alter_ego")`. |

## Required plan revisions (before ticketing)

1. **B8 source-of-truth is now a BLOCKER, not "open".** Resolve BEFORE P3/B1: the LangGraph
   checkpointer must **replace** `message_repository` persistence (or a documented one-way sync),
   never dual-write. Sequence: **ADR (source-of-truth) → harness**, not harness-then-ADR.
   Also verify `deepagents.create_deep_agent` (graph.py:218) even **accepts a `checkpointer=`** —
   if not, B1 needs a different integration (or library patch).
2. **P2 skills relocation:** add a precondition AC — audit `_shared/` cross-references and all load
   paths (`phase_subagents.py`, `instruction_context_loader.py`, `runtime_skills.py`, Dockerfile
   `/app/skills/runtime`, CI skill-path gate) and produce a skill→file dependency graph BEFORE
   moving anything. A wrong move = prod `FileNotFoundError` on deploy (auto-deploys).
   Confirm whether repo-root symlinks are consumed by ANY prod path (they're not — code resolves
   `get_runtime_skills_filesystem_root()`); if dead, drop them and don't let them shape the layout.
3. **B2+B3 split-brain:** "skills co-located but tools in application/" needs a FORMAL contract
   (skill = what the agent reads; tool = adapter delegating to an `application/` service via
   Protocol). If a tool is used by exactly one agent, consider moving its adapter into the package;
   keep `application/tools/` for genuinely shared tools only. Decide this rule explicitly.
4. **C1/C2 DeepSeek:** do NOT use `.with_fallbacks([claude])` for the tier boundary — it makes
   cost + quality unmonitorable (you pay DeepSeek+Claude on degradation; Claude grades Claude →
   circular quality signal). Use a **deterministic phase→model map** chosen before invocation,
   logged with a primary/fallback Langfuse tag, plus an explicit A/B quality-parity check vs the
   ≥70 persona gate before committing. For PRODUCTION, default to **direct DeepSeek API**
   (`api.deepseek.com`) or a cloud marketplace; gate the **opencode Zen** gateway to **dev-only**
   (ToS/SLA/data-residency unreviewed for routing user content through a third-party gateway).
   MUST integration-test JSON/structured-output + tool-calling through whichever endpoint
   (`source_synthesis_agent.py:55-68` hard-fails `ERR_INVALID_JSON`, no graceful degrade).
5. **B6 runtime QA:** even though the human chose "every generation", it MUST be **best-effort /
   non-blocking** — write the report to a side table; a Playwright crash/timeout must NOT fail the
   user's generation (droplet Chromium crashes have precedent — see `InMemorySaver` fallback in
   `app_factory.py:167`). Reconsider sampled cadence after a baseline week. Scope what "quality
   report" means (screenshot/DOM/LLM-scored — an LLM-scored reviewer doubles per-gen cost).

## Net
Plan is sound in DIRECTION but BLOCKED on execution detail. Re-validate the arch-plan's current-state
section against this file, fix the 5 revisions, then emit tickets (P1 prompts + the corrected P2 are
still the safe first phase; P3 harness is gated on the source-of-truth ADR).
