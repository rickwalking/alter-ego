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

## Detailed plan

[agentic-delivery-system-implementation-plan.md](./agentic-delivery-system-implementation-plan.md)

## ADR

[0008-agentic-delivery-workflow.md](../decisions/0008-agentic-delivery-workflow.md)
