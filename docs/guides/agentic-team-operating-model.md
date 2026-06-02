# Agentic Team Operating Model

How humans and agents deliver work in Alter-Ego using repo-backed tickets and skills.

## Principles

1. **Repo files are canonical** — Not chat memory or Kanban alone.
2. **Minimum rigor per tier** — Match process to risk and scope.
3. **Human merges** — Agents prepare PRs; humans approve merge and release.
4. **Evidence before Review** — Dev summary + QA report required for Review status.

## Work tiers

| Tier | Name | When | Typical skills |
|------|------|------|----------------|
| T0 | Trivial | Typo, comment, one-line config | `developer-skill` |
| T1 | Hotfix | Clear repro, isolated fix | `developer-skill` → `qa-agent` (lite) |
| T2 | Standard | Feature, skill update | `architect-skill` (optional) → `developer-skill` → `qa-agent` |
| T3 | Epic | Multi-module, ADR, migration | Full pipeline + `orchestrator-skill` |

See [agentic-delivery-system-implementation-plan.md](../plans/agentic-delivery-system-implementation-plan.md) for skip matrix.

## Default flow (T3)

```text
Intake → Shaping (Planner) → Planning (Architect) → Ready (Ticket Writer)
  → In Development (Developer) → Dev Complete → QA Running → Review → Ready to Merge → Done
```

`Needs Fixes` loops back to In Development. `Blocked` is Orchestrator-owned.

## Architect modes (optional)

| Mode | Command | Purpose |
|------|---------|---------|
| Plan | `/architect-skill` | ADR check, technical plan |
| Validate | `/architect-skill validate` | Pre-dev plan/ticket gate |
| Research | `/architect-skill research` | Trade-offs from docs/GitHub/web |
| Skeptical | `/architect-skill skeptical` | Cross-LLM cold critic |
| Bugfix design | `/architect-skill bugfix` | Fix approach before code (no edits) |

## High-risk areas (always full QA)

Listed in `.agent/config.yaml`: authentication, authorization, database migrations, LangGraph workflow state, prompts, LLM provider changes, publishing, scheduling, file uploads, deployment.

## WIP limits (solo default)

- In Development: 1
- QA Running: 1
- Planning: 1

Team defaults are in `.agent/config.yaml`.

## References

- [ticket-writing-guide.md](./ticket-writing-guide.md)
- [kanban-agent-workflow.md](./kanban-agent-workflow.md)
- [qa-checkpoints.md](./qa-checkpoints.md)
