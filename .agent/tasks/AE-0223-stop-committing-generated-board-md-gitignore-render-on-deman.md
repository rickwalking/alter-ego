# AE-0223 — Stop committing generated BOARD.md; gitignore + render on demand

Status: Intake
Tier: T1
Priority: Medium
Type: Quality
Area: Agent Workflow
Owner: Unassigned
Branch: TBD
Created: 2026-06-18
Updated: 2026-06-18
Source: kaizen session-2026-06-18b (P2, class FC3) — `.agent/reports/kaizen-session-2026-06-18b.plan.md`

## Goal

Eliminate the regressed-board failure class entirely by treating `.agent/BOARD.md`
as a local-only generated artifact instead of committed state.

## Problem

`.agent/BOARD.md` is a **git-tracked generated artifact** — `render_board.py`
rebuilds it from the `Status:` field of `.agent/tasks/*.md`. In the AE-0216 session
a developer branched off `origin/main` while several tickets existed only on an
unmerged branch, ran `render_board.py`, and the board was re-rendered **dropping the
unmerged tickets' cards** — a regressed board that nearly got committed.

A CI freshness gate was considered and **rejected** (kaizen Phase 3.6 cold-critic,
verified against live code): because the board is rendered from current-branch
tickets, a re-render-then-commit of the regressed board would pass a `--check` gate
(in-memory render == committed board), and the gate would also false-positive on
unrelated branches whose inherited board references tickets living elsewhere. The
durable, canonical state is the tickets themselves (`.agent/tasks/`); per
`CLAUDE.md` the visual Kanban is explicitly **optional**. So the board need not be
committed at all.

## Scope

- `git rm --cached .agent/BOARD.md` (stop tracking; keep the local file).
- Add `.agent/BOARD.md` to `.gitignore`.
- Provide a convenient render entrypoint (e.g. a `make board` target or a documented
  `uv run python scripts/agent_tasks/render_board.py` one-liner) so it's trivial to
  regenerate on demand.
- Update any skill/docs that reference a *committed* `BOARD.md` (search
  `skills/`, `docs/`, `CLAUDE.md`, `AGENTS.md`) to say it is generated locally and
  no longer tracked. The canonical board state remains `.agent/tasks/*.md`.

## Non-Goals

- Do not refactor unrelated code
- Do not change `render_board.py`'s rendering logic (only how the output is tracked)
- Do not remove `validate_all_tickets.py` / the `agent-gate` (ticket hygiene stays)

## Acceptance Criteria

- [ ] `.agent/BOARD.md` is no longer tracked (`git ls-files .agent/BOARD.md` empty)
      and is listed in `.gitignore`.
- [ ] A documented one-step render command exists and regenerates the board locally.
- [ ] All references to a committed `BOARD.md` in `skills/`, `docs/`, `CLAUDE.md`,
      `AGENTS.md` are updated (board is local/generated; tickets are canonical).
- [ ] `validate_all_tickets.py` still passes; no CI job depends on a committed `BOARD.md`.

## Classification (AE-0153 / AE-0180)

Repo-hygiene/tooling change with **no application behavior change** (AE-0153: no
`.feature`). It **removes** the failure class rather than adding a static-analysis
rule, so AE-0180's rule-fires test does not apply — the proof is that the file is
untracked + gitignored and no CI job references it.

## Decision Log

- **2026-06-18 — Gitignore over a freshness gate.** External cold-critic BLOCKED the
  freshness-gate design (P2 original): it was an inverse detector (passed the
  regressed-board case) and false-positived on cross-branch boards. Findings 1 & 2
  verified against `render_board.py` live. Gitignore removes the class with the least
  complexity and highest certainty (user direction). Trade-off accepted: the
  GitHub-web-viewable board is lost; canonical state is `.agent/tasks/`.
- See `.agent/reports/kaizen-session-2026-06-18b.skeptical-review.md` for the full review.

## Repro Steps

1. With tickets present only on an unmerged branch, check out a branch off `origin/main`.
2. Run `render_board.py`; observe `.agent/BOARD.md` lose the unmerged tickets' cards.

## Affected Areas

- [ ] Backend
- [ ] Frontend
- [ ] Tests

## Dependencies

None.

## Progress Log

### 2026-06-18

Ticket created from kaizen session-2026-06-18b (P2), re-scoped after the Phase 3.6
cold-critic BLOCKED the original freshness-gate design.

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Blockers

None.

## References

- Kaizen plan: `.agent/reports/kaizen-session-2026-06-18b.plan.md` (P2)
- Cold-critic review: `.agent/reports/kaizen-session-2026-06-18b.skeptical-review.md`
- Code: `scripts/agent_tasks/render_board.py`, `scripts/agent_tasks/constants.py` (`BOARD_PATH`)
