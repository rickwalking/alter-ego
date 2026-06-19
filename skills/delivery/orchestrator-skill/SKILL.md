---
name: orchestrator-skill
description: "Manage agentic delivery workflow: ticket status, BOARD.md, WIP limits, handoffs, and tier routing. Use when coordinating multiple agents, moving tickets, detecting blockers, or enforcing transition guards. Never implements production code."
version: 1.0.0
---

# Orchestrator Skill

## Purpose

Own delivery workflow across ticket states, board state, dependencies, and handoffs.

## When to use

- Starting T3 epics
- Moving tickets between columns
- WIP limit checks
- Routing to planner, architect, developer, QA, release manager
- Unblocking or escalating tier

## When NOT to use

- Writing application code
- Replacing `/developer-skill` or `/qa-agent`

## Prerequisites

Read `.agent/config.yaml`, the `.agent/tasks/AE-*.md` ticket files (canonical),
and recent `.agent/reports/`. `.agent/BOARD.md` is a generated, gitignored view —
regenerate it with `make board` if you want the rendered snapshot; don't rely on
it being committed.

## Workflow

1. Read active ticket and tier from ticket file (`Tier: T0|T1|T2|T3`).
2. Apply skip matrix from `docs/guides/agentic-team-operating-model.md`.
3. Before status change, run:
   `uv run python scripts/agent_tasks/validate_ticket.py AE-####`
   or `move_ticket.py` (enforces guards).
4. Regenerate the local `.agent/BOARD.md` via `make board` after bulk changes
   (generated view, not committed).
5. Record handoff in ticket `Decision Log`.

## WIP limits

Enforce counts in `.agent/config.yaml`. If over limit, mark ticket `Blocked` with reason.

## Handoff template

```markdown
## Orchestrator Handoff
Ticket: AE-####
From: <status> → To: <status>
Next skill: <skill-name>
Blockers: ...
Notes: ...
```

## References

- `docs/guides/agentic-team-operating-model.md`
- `docs/plans/agentic-delivery-system-implementation-plan.md`
