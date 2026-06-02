# Kanban Agent Workflow

Visual boards (Cline Kanban, Vibe Kanban, etc.) orchestrate work; **`.agent/BOARD.md` and ticket files are canonical**.

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

```bash
uv run python scripts/agent_tasks/render_board.py
```

## Auto-commit policy

Allowed without human gate: docs-only, ticket metadata, tests-only (see `.agent/config.yaml`).

Forbidden: migrations, auth, deployment, dependency upgrades, prompt behavior changes.

## Human review

Required for merge, release, and all high-risk areas.
