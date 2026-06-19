# AE-0250 — Per-agent facade packages plus wired memory and the skill/tool contract

Status: Intake
Tier: T3
Priority: High
Type: Refactor
Area: backend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-18
Updated: 2026-06-18

## Goal

Introduce per-agent façade packages (`alter_ego_agent/`, `carousel_agent/`, `shared/`)
that compose orchestration + prompts + skills + thin tool adapters, wire a per-agent
`memory=` `AGENTS.md` file (registry-loadable, deduped vs the system prompt), and
enforce the ADR-0016 skill/tool contract — without moving any infrastructure into the
agent packages.

## Problem

The user wants a per-agent mental model (`alter_ego_agent/`, `carousel_agent/` each with
skills/tools/agents/utils/prompts), but a self-contained package that absorbs
`application/tools/carousel/` (which calls infra) would **straddle Clean Architecture
layers** (ADR-009) and re-create the split-brain ADR-009 avoided. The skeptical pass
required the "skills here, tools there" boundary to become a **formal contract**
(ADR-0016): skill = content the agent reads (lives in the package); tool = a `@tool`
adapter delegating to an `application/` service via Protocol (business logic + infra
stay in `application/`/`infrastructure/`). Separately, `agents/AGENTS.md` is a latent
DeepAgents `memory=` file that **no code loads** (`grep` → 0 hits) — it should become a
per-agent, intentionally-wired `memory=` file, deduped against the system prompt.

Evidence: arch-plan §3.1 (AGENTS.md unwired), §8.1–§8.3 (tension + reconciliation +
formal contract); ADR-0016; skeptical-corrections.md §3.

## Scope

- Create façade packages under `agents/`: `alter_ego_agent/` (KB-only),
  `carousel_agent/` (orchestrator + subagents + nodes), `shared/` (persona/quality/
  feedback agents reused by multiple packages) — **orchestration only**.
- Wire a per-agent `memory=` `AGENTS.md` per package (registry-loadable `.md`), deduped
  vs `rag/v1/system.md` / `alter_ego/v3/system.md`.
- Apply the ADR-0016 skill/tool contract: single-agent tool adapters MAY co-locate in
  the agent package (thin façades); `application/tools/` keeps only genuinely shared
  tools (e.g. knowledge-base search/list on both RAG + AlterEgo).
- Keep `application/services/carousel/*` (70+ files) and infra in `application/` — the
  packages import builders, never absorb infra.

## Non-Goals

- Do **not** move `application/tools/` business logic or services into the agent
  packages — that inverts the dependency direction and violates ADR-009 (arch-plan §8.2
  "Conflict to flag"). The package is an orchestration façade, not a vertical slice.
- Do not fork prompts per agent — prompts stay in the shared registry
  (`agents/prompts/<domain>/`).
- Do not change agent behavior — this is reorganization + intentional memory wiring with
  behavior parity.
- Do not build the runtime QA subagent (AE-0251).

## Acceptance Criteria

- [ ] `alter_ego_agent/`, `carousel_agent/`, `shared/` packages exist holding
      orchestration only (agent classes, subagent specs, nodes, utils); imports still
      flow `domain → application → infrastructure → api` (no inverted imports).
- [ ] Each agent loads a per-agent `memory=` `AGENTS.md` via the harness memory loader;
      the memory file is deduped vs the system prompt (no double-instruction).
- [ ] The ADR-0016 skill/tool contract holds: any co-located tool adapter is a thin
      `@tool` delegating to an `application/` service via Protocol (asserted by a
      boundary check); `application/tools/` retains only shared (≥2-agent) tools.
- [ ] A boundary/import test (or the existing circular/boundary gate) confirms the agent
      packages contain **no** persistence/network/DB code.
- [ ] Agent behavior parity: existing agent integration tests pass unchanged; backend
      `pytest`/`mypy`/`ruff` + boundary gates green.

## Gherkin Scenarios

> Behavior-changing (per-agent `memory=` now loads into agent context — observable
> steering change) plus an architecture-boundary contract, so a `.feature` IS required.

```gherkin
Feature: Per-agent facade packages honor the skill/tool contract

  Scenario: An agent loads its per-agent memory file
    Given the alter_ego_agent package defines an AGENTS.md memory file
    When the agent is built via the harness
    Then the memory content is loaded into the agent context
    And it does not duplicate instructions already in the system prompt

  Scenario: A co-located tool adapter contains no infra
    Given a carousel_agent tool adapter
    When the boundary check runs
    Then the adapter only delegates to an application service via a Protocol
    And the package imports no persistence, network, or DB code

  Scenario: Shared tools stay in application/tools
    Given the knowledge-base search tool used by two agents
    When the contract is checked
    Then that tool remains under application/tools, not a single agent package
```

## Delta

### ADDED

- `agents/alter_ego_agent/`, `agents/carousel_agent/`, `agents/shared/` packages.
- Per-agent `AGENTS.md` memory files (deduped); a boundary/contract check.

### MODIFIED

- Agent build paths to load per-agent `memory=`; call sites updated to the new package
  layout; single-agent tool adapters relocated into their package.

### REMOVED

- The unwired top-level `agents/AGENTS.md` masquerading as runtime config (moved to a
  per-agent memory file or `docs/` per the dedupe decision).

## Affected Areas

- Backend: `agents/*` reorganization, harness memory loader, boundary check.
- Frontend: none.
- Database: none.
- API: none.
- Tests: boundary/contract test + existing agent integration tests (parity).
- Docs: ADR-0016 reference; package READMEs.
- Prompts/LLM: per-agent `memory=` files (deduped vs system prompts).
- Observability: none new.
- Deployment: import-path churn — ensure the composition root resolves the new layout.

## Dependencies

- Provisional epic id: **RES-11** (Phase 5).
- Gating ADR: **ADR-0016 (per-agent façade packages + formal skill/tool contract)**.
- Blocked by: **AE-0248 (RES-9, harness)** (memory loader + builder) and **AE-0249
  (RES-10, taxonomy)** (the subagents the carousel package composes). The co-located
  skill layout from **AE-0246 (RES-8)** should be in place.
- Blocks: **AE-0251 (RES-12)** benefits from the packages existing.
- Related: ADR-009 (Clean Architecture), the circular/boundary CI gates.

## Implementation Plan

1. Create the three packages (orchestration only); move agent classes/subagents/nodes.
2. Wire per-agent `memory=` `AGENTS.md` via the harness loader; dedupe vs system prompts.
3. Relocate single-agent tool adapters into their package as thin `@tool` façades; keep
   shared tools in `application/tools/`.
4. Add the boundary/contract check; run parity tests + boundary gates.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested (no inverted imports; memory dedupe; shared-tool placement)
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-18 21:30

Created from the agent-architecture-restructure epic (RES-11). Strict façade — no infra
moves; enforces the ADR-0016 skill/tool contract.

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Decision Log

- **Strict façade, no infra moves (ADR-0016 + ADR-009).** Absorbing `application/tools/`
  into the package would invert imports and re-create the split-brain ADR-009 avoided.
  The package is orchestration + prompts + skills + thin adapters only; the boundary
  check enforces it.
- **AGENTS.md → per-agent `memory=`, deduped.** It is currently unwired
  documentation drift; wiring it as memory must dedupe vs the system prompt to avoid
  double-instruction/token waste (arch-plan §3.1/§12).

## Test Classification (CLAUDE.md AE-0153 / AE-0180)

- **Behavior-changing** — per-agent `memory=` now loads into agent context (observable
  steering change), plus a new architecture-boundary contract. **`.feature` REQUIRED**
  (memory load + dedupe; adapter-no-infra; shared-tool placement).
- The boundary/import contract is additionally enforced by a check test (the circular/
  boundary gate) — complements the `.feature`.
- **Affected gates:** backend `pytest`/`mypy`/`ruff` + circular/boundary gates.

## Blockers

None (sequenced after AE-0248 + AE-0249).

## Final Summary

Pending.
