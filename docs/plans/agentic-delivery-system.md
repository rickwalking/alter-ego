# Agentic Delivery System (Operator Overview)

Persistent, tiered, multi-agent delivery for Alter-Ego.

## Quick start

1. Classify work: T0 (trivial) → T3 (epic). See [agentic-team-operating-model.md](../guides/agentic-team-operating-model.md).
2. Create ticket: `uv run python scripts/agent_tasks/create_ticket.py --title "..." --tier T2`
3. Implement: `/developer-skill` with `.agent/active-task.md` pointing at ticket
4. Validate: `/qa-agent`
5. Release prep: `/release-manager-skill`
6. Human: PR, merge, mark Done

## Where things live

| Artifact | Path |
|----------|------|
| Tickets | `.agent/tasks/AE-####.md` |
| Board | `.agent/BOARD.md` |
| Dev / QA reports | `.agent/reports/` |
| Plans | `docs/plans/` |
| ADRs | `docs/decisions/` |
| Skills | `skills/` |

## Skills

| Skill | Role |
|-------|------|
| `orchestrator-skill` | Status, WIP, handoffs |
| `planner-skill` | Epic breakdown (T3) |
| `architect-skill` | Plan, research, validate, skeptical, bugfix design |
| `ticket-writer-skill` | Ticket files |
| `developer-skill` | Implementation |
| `qa-agent` | Post-dev validation |
| `release-manager-skill` | PR / release prep |

## Ticket status lifecycle

Every ticket's `Status:` must be one of these values (enforced by
`scripts/agent_tasks/schema.py`; an invalid value is rejected with the full list):

```
Intake → Shaping → Ready → Planning → In Development → Dev Complete
       → QA Running → Needs Fixes → Blocked → Review → Ready to Merge → Done
       (Cancelled)
```

- **New tickets enter at `Intake`** — not `Todo` (which is not a valid status).
- **`Ready` is T0-only** as an entry state; for T1–T3 a ticket reaches `Ready`
  only once its required sections + acceptance criteria are present.
- `Review` requires a dev-summary and a QA report under `.agent/reports/`.

## Detailed plan

[agentic-delivery-system-implementation-plan.md](./agentic-delivery-system-implementation-plan.md)

## ADR

[0008-agentic-delivery-workflow.md](../decisions/0008-agentic-delivery-workflow.md)
