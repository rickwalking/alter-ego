# Kanban Agent Workflow

Visual boards (Cline Kanban, Vibe Kanban, etc.) orchestrate work; **the ticket
files in `.agent/tasks/` are the canonical state**. `.agent/BOARD.md` is a
**generated, gitignored view** of those tickets — regenerate it locally with
`make board`; never hand-edit or commit it (AE-0223).

## Card convention

- **Title:** `AE-0001 — Short title`
- **Description:** Path to ticket, branch, agent lane
- **Labels:** `backend`, `frontend`, `docs`, `qa`, `adr`, `migration`, `agent-workflow`

Example description:

```text
Path: .agent/tasks/AE-0001-agentic-delivery-system.md
Branch: feat/ae-0001-agentic-delivery
Lane: planner → architect → developer → qa → release
```

## One card = one ticket = one branch

- Branch: `feat/ae-####-slug`, `fix/ae-####-slug`, `docs/ae-####-slug`
- Prefer git worktree per card when running parallel agents

## Sync board from tickets

The board is generated, not committed — regenerate the local view on demand:

```bash
make board   # or: uv run python scripts/agent_tasks/render_board.py
```

## Auto-commit policy

Allowed without human gate: docs-only, ticket metadata, tests-only (see `.agent/config.yaml`).

Forbidden: migrations, auth, deployment, dependency upgrades, prompt behavior changes.

## Human review

Required for merge, release, and all high-risk areas.
