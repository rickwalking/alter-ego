# Ticket Writing Guide

Tickets live at `.agent/tasks/AE-####-slug.md`. Use scripts or copy templates manually.

## Templates

| Tier | Template |
|------|----------|
| T2/T3 | `.agent/tasks/_template.md` |
| T1 | `.agent/tasks/_template.hotfix.md` |

## Required sections (T2+)

- Goal, Problem, Scope, Non-Goals
- Acceptance criteria (testable, copy-paste commands)
- Affected areas
- Dependencies
- QA checklist

## Acceptance criteria (EARS-style)

Prefer:

```text
WHEN <trigger> THE SYSTEM SHALL <behavior>
```

Examples:

- `WHEN user opens public chat without auth THE API SHALL return 200 with session token`
- `WHEN validate_all_tickets.py runs on invalid Review ticket THE command SHALL exit 1`

## Gherkin

Required when **behavior changes**. Include happy path + at least one failure path.

## Delta block (brownfield)

```markdown
## Delta
### ADDED
- ...
### MODIFIED
- ...
### REMOVED
- ...
```

## Creating tickets

```bash
uv run python scripts/agent_tasks/create_ticket.py \
  --title "Short title" --type feature --area backend --tier T2
```

## References

- [agentic-team-operating-model.md](./agentic-team-operating-model.md)
