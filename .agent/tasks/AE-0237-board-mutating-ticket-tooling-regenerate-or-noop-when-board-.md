# AE-0237 — Board-mutating ticket tooling: regenerate-or-noop when BOARD.md absent + unit tests

Status: Review
Tier: T2
Priority: High
Type: Quality
Area: Cross-cutting
Owner: Unassigned
Agent Lane: developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-18
Updated: 2026-06-18

## Goal

Ticket creation and movement must never crash when the generated `.agent/BOARD.md`
is absent, and the board-mutating code path must be covered by unit tests so a
future change to the board's lifecycle cannot silently break the delivery workflow.

## Problem

Failure class **FC-1** (kaizen session-2026-06-18c). AE-0223 gitignored + `git rm`'d
`.agent/BOARD.md`, but `add_to_board()` (`scripts/agent_tasks/create_ticket.py:40`)
and `update_board()` (`scripts/agent_tasks/move_ticket.py:83`) still call
`board_path.read_text()` **unconditionally** → `FileNotFoundError` on any fresh
clone / CI / post-merge checkout where the gitignored board is absent. Net effect:
**`create_ticket.py` and `move_ticket.py` crash whenever the board file is missing.**
This shipped invisibly because the existing `pytest tests/unit/agent_tasks/` gate
(`agent-ticket-hygiene.yml`) covers only `schema` + `move_ticket.scaffold_dev_summary`
— it never exercises `add_to_board` / `update_board` / `next_ticket_id`. This is the
TOP-PRIORITY open bug recorded in the latest handoff; `make board` is the current
manual workaround.

Reports: `.agent/reports/kaizen-session-2026-06-18c.{signal,plan,skeptical-review}.md`.

## Scope

- `scripts/agent_tasks/create_ticket.py` — `add_to_board`.
- `scripts/agent_tasks/move_ticket.py` — `update_board`.
- `scripts/agent_tasks/render_board.py` — atomic write (see Decision Log, critic finding).
- `backend/tests/unit/agent_tasks/` — new/extended unit tests.

## Non-Goals

- No change to the board's column model, the kanban schema, or the gitignore decision
  (AE-0223 stands — the board stays a generated, non-committed view).
- No change to ticket-file (canonical) format.

## Acceptance Criteria

- [x] When `.agent/BOARD.md` is absent, `add_to_board` and `update_board` **regenerate
      it first** via `render_board` (the board is a generated view of `.agent/tasks/`),
      then apply their mutation — and never raise `FileNotFoundError`.
- [x] Board writes are **atomic** (write a temp file, then `os.replace`) in
      `render_board`, `add_to_board`, and `update_board` (critic TOCTOU mitigation).
- [x] New `backend/tests/unit/agent_tasks/test_create_ticket.py` covers `next_ticket_id`
      and `add_to_board` with the board **present AND absent**; `test_move_ticket.py`
      extends to `update_board` with the board **present AND absent**.
- [x] **Seeded-regression proof:** the absent-board test FAILS on the current code
      (reproduces `FileNotFoundError`) and PASSES after the fix.
- [x] Tests monkeypatch `BOARD_PATH`/`TASKS_DIR` to `tmp_path` — they never touch the
      real `.agent/` tree (critic: avoid TDD-vs-real-tree coupling).
- [x] `uv run pytest tests/unit/agent_tasks/ -q` green; `validate_all_tickets.py` green.

## Gherkin Scenarios

```gherkin
Feature: Ticket tooling survives an absent generated board

  Scenario: Creating a ticket when BOARD.md does not exist
    Given the .agent/BOARD.md file is absent
    When create_ticket.py allocates and writes a new ticket
    Then the board is regenerated from the ticket files
    And the new ticket id appears in the board
    And no FileNotFoundError is raised

  Scenario: Moving a ticket when BOARD.md does not exist
    Given the .agent/BOARD.md file is absent
    When move_ticket.py changes a ticket's status
    Then the board is regenerated and reflects the new status
    And no FileNotFoundError is raised
```

## Delta

### ADDED
- `backend/tests/unit/agent_tasks/test_create_ticket.py`.
- Atomic-write helper (temp + `os.replace`) shared by the board writers.

### MODIFIED
- `add_to_board` / `update_board`: regenerate-or-noop when the board is absent.
- `render_board.main`: atomic write.
- `backend/tests/unit/agent_tasks/test_move_ticket.py`: `update_board` coverage.

### REMOVED
- None.

## Affected Areas

- Backend: agent_tasks scripts + their unit tests.
- Frontend: none.
- Database: none.
- API: none.
- Tests: `backend/tests/unit/agent_tasks/`.
- Docs: none (behavior of the tooling is unchanged for the present-board case).
- Deployment: none.

## Dependencies

- Blocks: clean ticket creation on `main` after PR #54 lands (AE-0223 fallout).
- Blocked by: none.
- Related: AE-0223 (gitignored board), AE-0169 (move_ticket scaffold), AE-0181.

## Implementation Plan

1. Extract an atomic `_write_board(path, text)` (temp + `os.replace`).
2. In `add_to_board`/`update_board`: if the board is absent, call `render_board.main()`
   (or its core) to materialize it, then read+mutate; write atomically.
3. Add the unit tests (present + absent board) with `tmp_path` monkeypatching; confirm
   the absent-board test fails pre-fix, passes post-fix.

## Test Classification (CLAUDE.md AE-0153 / AE-0180)

- **No public/user-visible behavior change** for the board-present path; the fix only
  removes a crash on the board-absent path. Pure tooling robustness — **unit tests
  suffice, no `.feature` required**.
- **Seeded-violation test:** the absent-board test reproduces the crash (fails pre-fix).
- **Affected gates:** `agent-ticket-hygiene.yml` (`pytest tests/unit/agent_tasks/`).
- Reviewer/QA to sign off on the no-`.feature` classification.

## QA Checklist

- [x] Security reviewed
- [x] Code quality reviewed
- [x] Acceptance criteria validated
- [x] Edge cases tested (board present, absent, malformed)
- [x] Orphan/unfinished code checked

## Progress Log

### 2026-06-18 21:00

Created by kaizen session-2026-06-18c (FC-1). Cold-critic (opencode) added the
atomic-write TOCTOU mitigation and the tmp_path-isolation requirement.

### 2026-06-18 23:30

Implemented (developer-skill wave). Extracted `board_io.py` (atomic `write_board`
+ `ensure_board`); wired `render_board`/`add_to_board`/`update_board`. Added
seeded absent-board tests. `pytest tests/unit/agent_tasks/` green (24 passed).

## Files Touched

- `scripts/agent_tasks/board_io.py` (NEW) — shared `render_board_text`, atomic
  `write_board` (temp + `os.replace`), and `ensure_board` (regenerate-when-absent).
- `scripts/agent_tasks/render_board.py` — thin CLI wrapper over `board_io`.
- `scripts/agent_tasks/create_ticket.py` — `add_to_board` calls `ensure_board` then
  writes atomically.
- `scripts/agent_tasks/move_ticket.py` — `update_board` calls `ensure_board` then
  writes atomically.
- `backend/tests/unit/agent_tasks/test_create_ticket.py` (NEW) — `next_ticket_id`
  + `add_to_board` present/absent + atomic (no temp left).
- `backend/tests/unit/agent_tasks/test_move_ticket.py` — `update_board` present/absent.

## Test Evidence

```
$ uv run pytest tests/unit/agent_tasks/ -q
24 passed, 1 skipped in 0.20s
```

Seeded-regression proof: `test_add_to_board_regenerates_when_board_absent` and
`test_update_board_regenerates_when_board_absent` exercise the absent-board path
that raised `FileNotFoundError` on the pre-fix `read_text()`-first code; they pass
post-fix. Tests monkeypatch `TASKS_DIR`/board path to `tmp_path` — the real
`.agent/` tree is never touched.

## QA Report

External wave QA (wave-kaizen-1): **PASS** over 2 rounds (round 1 WARN with one
minor finding F-1, resolved; confirmation round PASS, 0 findings). See
`.agent/reports/AE-0237.qa.md` → `.agent/reports/wave-kaizen-1.qa.md`.


## Decision Log

- **Critic [BLOCKER] concurrent-writer TOCTOU on BOARD.md** — RESOLVED by requiring
  atomic writes (temp + `os.replace`) in all three board writers. The board is a
  gitignored, regenerable view of the canonical `.agent/tasks/`, so a lost race is
  recoverable via `make board`; atomic write closes the silent-drop window cheaply.
- **Critic [BLOCKER] stacked-merge / TDD ordering trap** — RESOLVED: tests monkeypatch
  `BOARD_PATH` to `tmp_path` (never touch the real tree), and the fix + tests ship in
  the **same commit**. Land this ticket before any other ticket exercises the board
  writers in CI.
- **Critic [WARN] render_board drops unparseable tickets** — ACKNOWLEDGED: regenerate
  then *insert-if-missing* (the existing add path already appends the id), so the
  target id is present even if an unrelated file fails to parse. Low probability for
  serial CLI use; no lock added.

## Blockers

None.

## Final Summary

Pending.
