---
name: ticket-writer-skill
description: "Create or update .agent/tasks/AE-####.md from plans with acceptance criteria, Gherkin, QA checklist. Use after planner/architect. Does not write production code."
version: 1.0.0
---

# Ticket Writer Skill

## Purpose

Materialize plans into canonical ticket files.

## Rules

- Use `create_ticket.py` or copy `_template.md` / `_template.hotfix.md`.
- Every ticket: goal, problem, scope, non-goals, acceptance criteria.
- Gherkin required for behavior changes.
- Run `validate_ticket.py` before setting Status: Ready.
- Do not set Ready if validation fails.

## Commands

```bash
uv run python scripts/agent_tasks/create_ticket.py --title "..." --tier T2 --type Feature --area backend
uv run python scripts/agent_tasks/validate_ticket.py AE-####
uv run python scripts/agent_tasks/render_board.py
```

## Handoff

```markdown
## Handoff to Developer
Ticket: AE-####
Status: Ready
Acceptance criteria: (list)
Branch: feat/ae-####-slug
```

## References

- `docs/guides/ticket-writing-guide.md`
- `.agent/tasks/_template.md`
