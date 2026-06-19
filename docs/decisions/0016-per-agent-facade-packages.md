# ADR-0016: Per-Agent Façade Packages + Formal Skill/Tool Contract

## Status

Accepted

## Context

The restructure introduces per-agent packages (`alter_ego_agent/`, `carousel_agent/`,
`shared/`) to give a per-agent mental model. The risk: a self-contained
`carousel_agent/` that absorbs `tools/` (which today live in
`application/tools/carousel/` and call infrastructure) would **straddle Clean
Architecture layers** (ADR-009) and invert the import direction — re-creating the
split-brain ADR-009 avoided. The skeptical pass
(`.agent/reports/agent-architecture.skeptical-corrections.md` §3) required this
informal "skills here, tools there" boundary to become a **formal contract**.

Today, tool builders live in `application/tools/<domain>/` (e.g.
`knowledge_base` search/list tools registered on both RAG and AlterEgo agents),
business logic + infra in `application/`/`infrastructure/`, and runtime skill
markdown under `skills/runtime/`. Prompts live in the shared registry
(`agents/prompts/<domain>/`).

## Decision Drivers

- A per-agent mental model without breaking Clean Architecture (ADR-009).
- No agent package may own persistence/network/DB code.
- A single, explicit rule for where a tool **adapter** lives, so packages don't drift
  into vertical slices that own infra.

## Decision

**Per-agent packages are orchestration FAÇADES** — they *reference* (never *absorb*)
the Clean-Architecture layers. Proposed layout under `agents/`:

```
agents/
├── harness/          # ADR-0015 shared composition surface
├── prompts/          # shared registry (UNCHANGED location — do NOT fork per agent)
├── alter_ego_agent/  # AGENTS.md (memory), agent.py, utils.py (KB-only)
├── carousel_agent/   # agent.py (orchestrator), subagents/, nodes/, utils.py
└── shared/           # persona/quality/feedback agents reused by ≥2 packages
```

`tools/` builders and the heavy `application/services/carousel/*` **stay in
`application/`**; agent packages import the builders.

**Formal skill/tool contract (the rule that prevents drift):**

- **Skill = what the agent READS.** Markdown instruction/standards context (phase
  `SKILL.md`, `_shared/*.md`). It is *content*, has no Python imports, and **lives in
  the agent package** it belongs to (co-location).
- **Tool = a LangChain `@tool` ADAPTER.** A thin function delegating to an
  `application/` service **via a Protocol**. It owns **no** business logic and **no**
  infra.
- **Placement rule for tool adapters:**
  - A tool adapter used by **exactly one agent** MAY live in that agent's package
    (e.g. `carousel_agent/tools/…`) — it's a thin façade over an `application/`
    service, so it imports no infra.
  - `application/tools/` keeps **only genuinely shared tools** (used by ≥2 agents,
    e.g. `knowledge_base` search/list on both RAG + AlterEgo).
- **Invariant:** wherever the adapter lives, business logic + infra stay in
  `application/`/`infrastructure/` behind a Protocol. The agent package contains only
  orchestration, prompts (via the shared registry), skills (content), and thin tool
  adapters — never persistence, network, or DB code.

Prompts are **not** forked per agent — they stay in the shared
`agents/prompts/<domain>/` registry (ADR-0013-era registry standard). Each agent's
`AGENTS.md` is wired as its `memory=` file (per the harness, ADR-0015), deduped
against its system prompt.

## Consequences

**Good:**

- Per-agent mental model achieved without violating ADR-009 import direction.
- The split-brain is closed by an explicit, enforceable placement rule.
- Shared tools (knowledge_base) stay shared; single-agent adapters co-locate cleanly.

**Bad / constraints:**

- Significant import churn across many call sites (P5 of the epic).
- A reviewer/lint check is advisable to enforce "no infra import inside an agent
  package" so the invariant doesn't erode.

## Related Decisions

- ADR-009 (Clean Architecture — the import-direction rule this honors).
- ADR-007 (DeepAgents consolidation — deterministic carousel nodes stay in place).
- ADR-0015 (harness; per-agent `memory=` AGENTS.md wiring).

## Open Questions (for human before proposed → accepted)

- Whether to add a lint/boundary gate asserting "no `infrastructure`/DB import inside
  `agents/<agent>/`", to make the invariant enforced rather than conventional.

## Tags

#agents #architecture #clean-architecture #skills #tools #facade
