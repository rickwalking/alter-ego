# AE-0566 — Bump msgpack for CVE-2026-114613

Status: In Development
Tier: T1
Priority: High
Type: Chore
Area: Backend
Owner: Kimi
Agent Lane: developer → qa → release
Branch: fix/ae-0566-msgpack-cve
Kanban Card: TBD
Created: 2026-10-27
Updated: 2026-10-27

## Goal

Restore `backend:pip-audit` to green by moving the existing transitive msgpack security floor to the first fixed release line.

## Problem

The locked msgpack 1.2.1 release is flagged by CVE-2026-114613. Its C extension retains a decoded map value when `strict_map_key` rejects a key, allowing repeated malformed inputs to grow process memory. The issue is fixed in msgpack 1.2.3 and blocks the existing pip-audit gate on PRs.

## Scope

- Raise `msgpack>=1.2.1` to `msgpack>=1.2.3` in `backend/pyproject.toml` and retain the existing trailing-note style while naming both the prior GHSA and this CVE.
- Run `uv lock --upgrade-package msgpack` so `backend/uv.lock` resolves msgpack 1.2.3 or later and review every lockfile change.
- Sync the environment, run pip-audit without a vulnerability ignore, and run the existing msgpack checkpoint deserialization tests.
- Produce developer and independent QA reports, open one PR, and require its CI checks to pass.

## Non-Goals

- No vulnerability ignores, application-code changes, schema changes, API changes, or unrelated dependency upgrades.
- No new feature behavior, live network test, or local mutation run.

## Acceptance Criteria

- [x] AC1 The project floor is `msgpack>=1.2.3`, the note names GHSA-6v7p-g79w-8964 and CVE-2026-114613, and the lock resolves msgpack 1.2.3+ without unrelated package upgrades.
- [ ] AC2 `backend:pip-audit` passes with no new ignore or suppression; any separate advisory is reported rather than hidden.
- [x] AC3 Existing msgpack checkpoint fixture/deserialization tests pass on the upgraded package.
- [ ] AC4 Independent QA passes and every PR workflow is green; mutation remains CI-only.

## No-`.feature` classification (dependency/CI ticket)

- (a) No public or user-visible behavior change: this is a patch-level dependency security repair using the existing LangGraph checkpoint serializer API.
- (b) Seeded-violation evidence: no gate or rule is added; the existing pip-audit gate already fails on the vulnerable version and is the regression sensor.
- (c) Affected gates: `backend:pip-audit` and `backend:test`.
- (d) Reviewer/QA sign-off on this classification: `.agent/reports/AE-0566.qa.md`.

## Delta

### ADDED

- None.

### MODIFIED

- Msgpack security floor, advisory note, and locked package artifacts.

### REMOVED

- Vulnerable msgpack 1.2.1 from the locked environment.

## Affected Areas

- Backend: dependency manifest and lockfile only.
- Frontend: none.
- Database: none.
- API: none.
- Tests: existing checkpoint fixture portability tests only; no test-file change required.
- Docs: ticket and delivery reports.
- Prompts/LLM: none.
- Observability: none.
- Deployment: dependency update through the normal build; no migration or one-shot.

## Dependencies

- Blocks: PRs blocked by the msgpack pip-audit failure.
- Blocked by: none.
- Related: AE-0540 backend dependency advisories.

## Implementation Plan

1. Create the ticket, update the msgpack floor and note, and relock only msgpack.
2. Review the lock diff, sync, run pip-audit and focused checkpoint tests, then reproduce required gates.
3. Complete independent QA, commit, push, open the PR, and watch CI.

## QA Checklist

- [x] Security reviewed
- [x] Code quality reviewed
- [x] Acceptance criteria validated
- [x] Edge cases tested
- [x] Orphan/unfinished code checked

## Progress Log

### 2026-10-27

Urgent fix-forward ticket created from current `origin/main` in a dedicated worktree. The existing checkpoint fixture uses LangGraph's msgpack serializer and provides focused compatibility coverage without adding application code.

The floor now resolves msgpack 1.2.4 through uv 0.13.5 with no other package upgrade and the existing lock revision retained. All three checkpoint portability tests pass, as do Ruff, strict mypy, and integrity. The audit no longer reports msgpack but remains red on the separate dnspython 2.8.0 advisory CVE-2026-114605 (fixed in 2.9.0); that package is outside this ticket and is reported rather than suppressed.

Independent external QA confirmed AC1 and AC3, the minimal lockfile, the checkpoint tests, and the no-`.feature` classification. It returned FAIL only because AC2 remains blocked by dnspython. PR CI is pending.

## Files Touched

- `backend/pyproject.toml`
- `backend/uv.lock`
- `.agent/active-task.md`
- `.agent/tasks/AE-0566-msgpack-cve.md`
- `.agent/reports/AE-0566.dev-summary.md`
- `.agent/reports/AE-0566.qa.md`

## Test Evidence

- `uv lock --upgrade-package msgpack` with uv 0.13.5: msgpack 1.2.1 → 1.2.4; no other package upgrade and lock revision 5 retained.
- `uv run pytest tests/unit/test_checkpoint_fixture_portability.py -q`: 3 passed.
- `uv run ruff format --check src/` and `uv run ruff check src/`: pass; `uv run mypy rag_backend/ --explicit-package-bases` from `backend/src`: 1,193 files pass.
- `check-integrity.sh backend`: 0 blockers, 0 warnings.
- `gates.sh backend:pip-audit`: FAIL only on dnspython 2.8.0 / CVE-2026-114605; msgpack no longer appears. No ignore was added.

## QA Report

[AE-0566.qa.md](../reports/AE-0566.qa.md) — FAIL, `mode: external`. The msgpack patch and no-`.feature` classification are accepted; the overall gate remains red on the separate dnspython advisory.

## Decision Log

- 2026-10-27 (Pedro): raise the existing transitive floor to msgpack 1.2.3+ and keep the change limited to that package.
- 2026-10-27 (implementation): allow the lock resolver to select the latest compatible 1.2.3+ patch while rejecting unrelated upgrades through diff review.

## Blockers

`backend:pip-audit` still reports dnspython 2.8.0 under CVE-2026-114605, fixed in 2.9.0. This is a separate dependency advisory outside the msgpack-only instruction and must be fixed separately before the overall gate and PR CI can pass.

## Final Summary

The existing msgpack floor is now `>=1.2.3`, both advisory IDs are documented, and the lock resolves 1.2.4 without other package upgrades. Three checkpoint portability tests, Ruff, strict mypy, and integrity pass. External QA validates the patch but the overall audit remains blocked by dnspython CVE-2026-114605, which requires a separate fix.
