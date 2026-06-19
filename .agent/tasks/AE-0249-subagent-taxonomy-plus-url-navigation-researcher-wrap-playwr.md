# AE-0249 — Subagent taxonomy plus URL-navigation researcher (wrap PlaywrightResearchTool as a tool)

Status: In Development
Tier: T2
Priority: High
Type: Feature
Area: backend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-18
Updated: 2026-06-18

## Goal

Formalize the subagent taxonomy and add a `researcher` subagent that can browse a URL
during carousel creation — by wrapping the existing `PlaywrightResearchTool`
(`scrape_url` / `search_web`) as LangChain `@tool`s — while keeping the deterministic
phases as raw LangGraph nodes (ADR-007).

## Problem

Carousel delegation has two parallel, partially-wired mechanisms (arch-plan §4.1): the
DeepAgents `task` path (parent → editorial subagent) and a phase subagent registry
(`phase_subagents.py:27`) that carries skill paths but **no executable tools/runnable**.
The repo already owns `PlaywrightResearchTool.scrape_url` + `search_web`
(`application/services/tools/research_tool.py`) but they are **not exposed as LangChain
tools to any subagent** — so a user cannot paste a URL and have the agent browse it
mid-creation. ADR-0015's taxonomy (per-job, isolated-context subagents) needs exactly
one new true subagent here: `researcher` with URL navigation. The deterministic phases
(design tokens, PDF export, DB sync, persona gate) must **stay LangGraph nodes** —
over-agentifying them would regress ADR-007's determinism/HITL guarantees.

Evidence: arch-plan §4.1–§4.3 (taxonomy table; "Key upgrade: URL navigation");
ADR-0015; ADR-007.

## Scope

- Wrap `PlaywrightResearchTool.scrape_url` and `search_web` as LangChain `@tool`
  adapters (thin façades over the existing service via Protocol).
- Define a `researcher` subagent (isolated context) granted those tools +
  `search_documents`, with the `phases/research` + `_shared/critical-rules` skill
  context.
- Align the subagent specs to the DeepAgents `tools`/`prompt`/`model` fields (today they
  carry a non-standard `skills` key only).
- Keep deterministic phases (outline/content tokens/export/DB/persona gate) as raw
  LangGraph nodes.

## Non-Goals

- Do **not** convert deterministic phases into autonomous subagents — only `researcher`
  (and later `qa_reviewer`, AE-0251) become true subagents (arch-plan §12).
- Do not add the runtime QA subagent here (AE-0251).
- Do not move tool business logic into the agent package — the `@tool` is a thin adapter
  delegating to the existing `application/` service via Protocol (ADR-0016 contract).
- Do not change the persona gate or export geometry.

## Acceptance Criteria

- [x] `scrape_url` and `search_web` are exposed as LangChain `@tool` adapters that
      delegate to `PlaywrightResearchTool` via a Protocol (no business logic in the
      adapter).
- [x] A `researcher` subagent runs in isolated context with those tools + the research
      skill context; given a URL it browses the page and returns synthesized sources.
- [x] Subagent specs use the DeepAgents `tools`/`prompt`/`model` fields (the
      half-wired `skills`-only specs are aligned).
- [x] Deterministic phases remain LangGraph nodes (a test asserts they are not
      `task`-delegated subagents) — ADR-007 determinism preserved.
- [x] Backend `pytest`/`mypy`/`ruff` green; a research-with-URL integration test passes
      (Playwright mocked/stubbed where keys/browser are unavailable in CI).

## Gherkin Scenarios

> Behavior-changing (new user-visible capability: paste a URL during creation), so a
> `.feature` IS required — happy + edge + failure.

```gherkin
Feature: A researcher subagent can browse a URL during carousel creation

  Scenario: The agent browses a pasted URL and synthesizes sources
    Given a user provides a URL during carousel research
    When the researcher subagent runs with the scrape_url tool
    Then it fetches the page content and returns synthesized sources

  Scenario: Deterministic phases stay LangGraph nodes
    Given the carousel workflow runs
    When the outline and export phases execute
    Then they run as deterministic LangGraph nodes, not task-delegated subagents

  Scenario: A scrape failure degrades gracefully
    Given the scrape_url tool fails on an unreachable URL
    When the researcher subagent runs
    Then the failure is reported and research continues without the URL
```

## Delta

### ADDED

- LangChain `@tool` adapters for `scrape_url` / `search_web`.
- A `researcher` subagent definition (tools + research skill context).
- Research-with-URL integration test.

### MODIFIED

- Subagent specs aligned to DeepAgents `tools`/`prompt`/`model` fields.

### REMOVED

- None.

## Affected Areas

- Backend: `application/services/tools/research_tool.py` (adapter wrap),
  subagent specs, `phase_subagents.py`.
- Frontend: none (URL is already a user input surface).
- Database: none.
- API: none (capability is internal to creation).
- Tests: research-with-URL integration test + determinism assertion.
- Docs: ADR-0015 taxonomy reference.
- Prompts/LLM: `researcher` prompt + research skill context.
- Observability: Langfuse trace tags for the researcher subagent.
- Deployment: Playwright must be available (already present for export geometry).

## Dependencies

- Provisional epic id: **RES-10** (Phase 4).
- Gating ADR: **ADR-0015 (subagent taxonomy + URL-navigation tool)**; ADR-007
  (deterministic nodes stay nodes).
- Blocked by: **AE-0248 (RES-9, harness)** — subagents are composed via the harness.
- Blocks: **AE-0250 (RES-11)** (façade packages consume the taxonomy) and **AE-0251
  (RES-12)** (`qa_reviewer` follows the same subagent pattern).
- Related: AE-0246 (co-located skills supply the research skill context).

## Implementation Plan

1. Wrap `scrape_url`/`search_web` as `@tool` adapters delegating via Protocol.
2. Define the `researcher` subagent (tools + research skill context); align spec fields
   to DeepAgents.
3. Add the URL-research integration test (mock Playwright in CI) + the determinism
   assertion.
4. Run gates.

## QA Checklist

- [ ] Security reviewed (URL fetching = SSRF surface; validate/limit fetched URLs)
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested (unreachable URL; deterministic phases stay nodes)
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-18 21:30

Created from the agent-architecture-restructure epic (RES-10). Only `researcher`
becomes a true subagent; deterministic phases stay LangGraph nodes (ADR-007).

### 2026-06-19 — Dev (developer-skill)

Implemented on `feat/agent-harness-ae0248` (stacks on AE-0248). The two web-research
@tool adapters and the `researcher` subagent live in the **agents** package and
depend on the `ResearchTool` **Protocol** (`domain/protocols/carousel.py`); DI
injects the concrete `PlaywrightResearchTool` (`application/`). No new
`agents -> application` edge — `lint-imports` stays **22 kept / 0 broken**. Phase
subagent specs aligned to DeepAgents `name`/`description`/`prompt`/`tools` fields
(the half-wired `skills`-only key removed). Deterministic phases stay LangGraph
nodes; a test asserts they are not task-delegated subagents. `.feature` added.

## Files Touched

ADDED:
- `src/rag_backend/agents/tools/__init__.py`, `constants.py`, `research_tools.py`
- `src/rag_backend/agents/subagents/__init__.py`, `constants.py`, `researcher.py`
- `tests/features/researcher_subagent_url_navigation.feature`
- `tests/unit/agents/test_researcher_subagent.py`
- `tests/integration/carousel_consolidation/test_researcher_url_navigation.py`

MODIFIED:
- `src/rag_backend/application/services/carousel/phase_subagents.py` (DeepAgents fields)
- `src/rag_backend/application/services/carousel/editorial_subagent.py` (prompt field)
- `tests/unit/application/test_carousel_pipeline_consolidation_unit.py` (assert prompt)

## Test Evidence

- `ruff check src/ tests/` → All checks passed.
- `mypy rag_backend/ --explicit-package-bases` → 0 issues (518 files).
- `lint-imports` → 22 kept, 0 broken (no new agents→application edge).
- `pytest tests/unit/agents tests/integration/carousel_consolidation
  tests/unit/application/test_carousel_pipeline_consolidation_unit.py` → 368 passed.
- `GATES_REQUIRE_ALL=1 check-integrity.sh backend` → 0 blockers, 0 warnings.

## QA Report

Pending.

## Decision Log

- **Only `researcher` is agentified here.** ADR-007 deliberately made phases
  deterministic nodes; converting them to subagents would regress determinism/HITL
  (arch-plan §12). The URL-navigation upgrade is the concrete user value, so it gets the
  new subagent.
- **Tool = thin adapter (ADR-0016).** The `@tool` delegates to the existing service via
  Protocol; no business logic moves into the agent package.
- **SSRF surface flagged** — URL fetching must be validated/limited in QA.

## Test Classification (CLAUDE.md AE-0153 / AE-0180)

- **Behavior-changing — new user-visible capability** (browse a URL during creation).
  **`.feature` REQUIRED** (happy: browse+synthesize; edge: deterministic phases stay
  nodes; failure: unreachable URL degrades gracefully).
- **Affected gates:** backend `pytest`/`mypy`/`ruff` + the research integration test.

## Blockers

None (sequenced after AE-0248).

## Final Summary

Pending.
