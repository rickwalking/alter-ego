# ADR-008: Agentic Delivery Workflow

## Status

Accepted

## Context

Alter-Ego uses AI agents for implementation (`developer-skill`, `qa-agent`) with strong constitution files (`CLAUDE.md`, ADRs) but no durable ticket orchestration. Agent session memory is ephemeral; Kanban tools provide visuals but not versioned truth. We need traceability (plans, QA evidence, handoffs) without forcing a heavyweight waterfall process on every bug fix.

## Decision

Adopt a **repo-backed agentic delivery system** with:

1. **Canonical state in Git** — `.agent/tasks/*.md`, `.agent/BOARD.md`, `.agent/reports/*.md`
2. **Visual Kanban as orchestration layer** — Cline/Vibe/similar; not source of truth
3. **Tiered workflow (T0–T3)** — Full pipeline for epics; fast paths for hotfixes
4. **Role skills** — Planner, Architect (hub modes), Ticket Writer, Orchestrator, Release Manager; extended Developer and QA
5. **Human merge gate** — No autonomous merge; high-risk areas always require full QA
6. **CI hygiene** — `validate_all_tickets.py` on `.agent/**` changes

Architect skill includes optional modes: skeptical (cross-LLM cold critic), research, bugfix-helper, validate — all read-only pre-dev.

## Consequences

**Good:**

- Agents resume work from tickets without chat history
- DEV → QA evidence chain is auditable
- Small fixes skip Planner/Architect overhead via T1
- Cross-model skeptical review reduces self-preference bias on plans

**Bad:**

- Ticket maintenance overhead on every change
- Risk of process theater if tiers are ignored
- External skeptical review requires manual CLI step (v1)

## Alternatives Considered

| Alternative | Why Rejected |
|-------------|--------------|
| Kanban-only (no repo tickets) | Not versioned; agents lose context |
| GitHub Issues as canonical | Duplicates plan content; weaker AC/Gherkin linkage |
| Always-linear pipeline | Too slow for hotfixes |
| Auto-merge on QA PASS | Unacceptable for auth, migrations, prompts |

## Related Decisions

- ADR-001: Adopt MADR for ADRs
- ADR-005: Adopt Mutation Testing

## Tags

#process #agents #workflow
