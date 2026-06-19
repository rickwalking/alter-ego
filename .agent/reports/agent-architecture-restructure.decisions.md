# Agent Architecture Restructure — Human Decisions (2026-06-18)

Companion to `.agent/reports/agent-architecture-restructure.arch-plan.md`. These resolve
the plan's "Open decisions for the human". Ticket emission (next session) must reflect them.

## Resolved

1. **Per-agent package scope → FAÇADE.**
   Agent packages (`alter_ego_agent/`, `carousel_agent/`, `shared/`) hold orchestration,
   prompts, subagent definitions, and the agent's `skills/` — **NOT** business-logic
   tools/services. `tools/` + services **stay in `application/`** (preserves Clean
   Architecture + ADR-009). The `skills/tools/agents/utils/prompts` sketch is honored at
   the façade level; `tools/` in the sketch maps to thin tool *adapters/wiring*, with the
   actual logic remaining in `application/`.

2. **Runtime agent skills placement → CO-LOCATE in agent packages.**
   Physically move the runtime skill folders (carousel-pipeline, carousel-refinement,
   knowledge-base) out of repo-root `skills/` into their owning agent package
   (e.g. `carousel_agent/skills/...`, `alter_ego_agent/skills/knowledge-base/...`), and
   update every loader path: `domain/constants/runtime_skills.py`,
   `application/services/carousel/phase_subagents.py`, `instruction_context_loader.py`,
   `rag_agent.py`, plus the Dockerfile copy paths and any CI skill-path gate. Repo-root
   `skills/` keeps ONLY delivery/process skills. Remove the empty `skills/runtime/`
   container and the root symlinks that intermixed the two kinds.
   ⚠️ This is the higher-touch option — verify the Docker image + CI skill-path checks
   after the move (prod resolves skills via these code paths, not the root symlinks).

3. **`AGENTS.md` → WIRE AS `memory=` AND locate per-agent.**
   Promote the (currently dead) `agents/AGENTS.md` into an actually-loaded DeepAgents
   `memory=`/system file, and give EACH agent its own such file inside its package
   (e.g. `alter_ego_agent/AGENTS.md` or `alter_ego_agent/prompts/system.md` wired as
   memory; `carousel_agent/` its own). Reconcile with the prompt-registry standard: the
   per-agent system/identity content should be registry-loadable (`.md` under the agent's
   `prompts/`) and passed as the agent's memory/system prompt — not an unloaded stray file.

4. **Runtime QA (Playwright carousel report) → EVERY GENERATION.**
   The `qa_reviewer` runtime subagent runs automatically on every completed carousel,
   producing a quality report that feeds the session handoff summary + the runtime kaizen
   channel. Budget for the browser launch cost; design it async/non-blocking to the user
   where possible (report attaches post-generation), and make it resilient (a QA failure
   must not fail the generation).

## Unresolved (still open — decide before/at the relevant phase)

- **Checkpoint source-of-truth (AE-0163 trap):** once chat agents get a checkpointer, is
  the LangGraph checkpoint or the message repository authoritative? Avoid dual-write.
  → resolve in the harness phase (P3) before wiring chat-agent persistence.
- **`/carousel-pipeline` as a human slash command?** Confirm whether any human/slash-command
  entrypoint references the runtime skills before relocating (decision 2) — if yes, keep a
  shim or update the command registration.

## Emission note
Follow the plan's 7-phase migration. Sequence: **P1 prompt consolidation** (move the 5
hardcoded prompts incl. quality_agent off-registry + anti-hardcoding checker w/ rule-fires
test) and **P2 skills relocation** first (low-risk, no ADR) — but note decision 2 makes P2
higher-touch than the plan's drop-symlinks default (add Docker/CI path-update ACs).
Then **P3 harness** (checkpointer/store/memory/middleware extraction) unlocks **P4 subagent
taxonomy + URL-nav researcher**, **P5 per-agent façade packages + per-agent memory**, and
**P6 runtime QA (every-generation) + runtime kaizen channel**. Emit the 6 proposed ADRs
(013–018) alongside their phases.
