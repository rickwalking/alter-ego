# AE-0566 — Bump msgpack and dnspython for CVE-2026-114613 / CVE-2026-114605

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

Restore `backend:pip-audit` to green by moving the existing transitive msgpack security floor to the first fixed release line, and add an equivalent transitive dnspython floor for the advisory that surfaced once msgpack cleared.

## Problem

Two locked transitive packages are flagged by new advisories:

- msgpack 1.2.1 (CVE-2026-114613, fixed in 1.2.3): its C extension retains a decoded map value when `strict_map_key` rejects a key, allowing repeated malformed inputs to grow process memory. Fixed in msgpack 1.2.3.
- dnspython 2.8.0 (CVE-2026-114605, fixed in 2.9.0): a crafted DNS message causes excessive CPU consumption in `dns.name.from_wire_parser`. Fixed in dnspython 2.9.0.

Both block the existing pip-audit gate on PRs.

## Scope

- Raise `msgpack>=1.2.1` to `msgpack>=1.2.3` in `backend/pyproject.toml` and retain the existing trailing-note style while naming both the prior GHSA and this CVE.
- Add a transitive floor `dnspython>=2.9.0` in `backend/pyproject.toml` next to the msgpack floor, in the same trailing-note style naming CVE-2026-114605.
- Run `uv lock --upgrade-package msgpack` and `uv lock --upgrade-package dnspython` so `backend/uv.lock` resolves the fixed releases and every lockfile change is reviewed.
- Sync the environment, run pip-audit without a vulnerability ignore, and run the existing msgpack checkpoint deserialization tests plus the identity/email-validation unit tests that exercise dnspython transitively.
- Produce developer and independent QA reports, open one PR, and require its CI checks to pass.

## Non-Goals

- No vulnerability ignores, application-code changes, schema changes, API changes, or unrelated dependency upgrades.
- No new feature behavior, live network test, or local mutation run.

## Acceptance Criteria

- [x] AC1 The project floor is `msgpack>=1.2.3`, the note names GHSA-6v7p-g79w-8964 and CVE-2026-114613, and the lock resolves msgpack 1.2.3+ without unrelated package upgrades.
- [x] AC2 The project floor is `dnspython>=2.9.0`, the note names CVE-2026-114605, and the lock resolves dnspython 2.9.0 without unrelated package upgrades.
- [x] AC3 `backend:pip-audit` passes with no findings and no new ignore or suppression.
- [x] AC4 Existing msgpack checkpoint fixture/deserialization tests and the identity email-validation unit tests pass on the upgraded packages.
- [ ] AC5 Independent QA passes and every PR workflow is green; mutation remains CI-only.

## No-`.feature` classification (dependency/CI ticket)

- (a) No public or user-visible behavior change: this is a patch/minor-level dependency security repair using the existing LangGraph checkpoint serializer API and dnspython only as a transitive dependency of email-validator.
- (b) Seeded-violation evidence: no gate or rule is added; the existing pip-audit gate already fails on the vulnerable versions and is the regression sensor.
- (c) Affected gates: `backend:pip-audit` and `backend:test`.
- (d) Reviewer/QA sign-off on this classification: `.agent/reports/AE-0566.qa.md`.

## Delta

### ADDED

- None.

### MODIFIED

- Msgpack and dnspython security floors, advisory notes, and locked package artifacts.

### REMOVED

- Vulnerable msgpack 1.2.1 and dnspython 2.8.0 from the locked environment.

## Affected Areas

- Backend: dependency manifest and lockfile only.
- Frontend: none.
- Database: none.
- API: none.
- Tests: existing checkpoint fixture portability and identity unit tests only; no test-file change required.
- Docs: ticket and delivery reports.
- Prompts/LLM: none.
- Observability: none.
- Deployment: dependency update through the normal build; no migration or one-shot.

## Dependencies

- Blocks: PRs blocked by the msgpack/dnspython pip-audit failure.
- Blocked by: none.
- Related: AE-0540 backend dependency advisories.

## Implementation Plan

1. Create the ticket, update the msgpack floor and note, and relock only msgpack.
2. Add the dnspython floor and note next to the msgpack floor, relock only dnspython, and review both lock diffs.
3. Review the lock diff, sync, run pip-audit and focused checkpoint/identity tests, then reproduce required gates.
4. Complete independent QA, commit, push, open the PR, and watch CI.

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

### 2026-10-27 (dnspython extension, Pedro's instruction)

Pedro extended the ticket to cover the second advisory surfaced by the same gate. Added the `dnspython>=2.9.0` transitive floor next to the msgpack floor with a trailing note naming CVE-2026-114605, relocked with the CI-pinned uv 0.13.5 (`uv lock --upgrade-package dnspython`), and reviewed the diff: dnspython 2.8.0 → 2.9.0 with its sdist/wheel artifacts plus the new direct floor entries in the project package block; no other package changed and lock revision 5 is retained.

`gates.sh backend:pip-audit` now reports no known vulnerabilities (PASS, fail=0). The 45 targeted tests (checkpoint portability + full identity suite) pass, as do Ruff, strict mypy (1,193 files), and integrity (0 blockers, 0 warnings). PR CI pending on the single push.

## Files Touched

- `backend/pyproject.toml`
- `backend/uv.lock`
- `.agent/active-task.md`
- `.agent/tasks/AE-0566-msgpack-cve.md`
- `.agent/reports/AE-0566.dev-summary.md`
- `.agent/reports/AE-0566.qa.md`

## Test Evidence

- `uv lock --upgrade-package msgpack` with uv 0.13.5: msgpack 1.2.1 → 1.2.4; no other package upgrade and lock revision 5 retained.
- `uv lock --upgrade-package dnspython` with uv 0.13.5: dnspython 2.8.0 → 2.9.0; lock diff touches only dnspython artifacts and the new direct floor entries; revision 5 retained.
- `uv run pytest tests/unit/test_checkpoint_fixture_portability.py tests/unit/modules/identity/ -q`: 45 passed.
- `uv run ruff format --check src/` and `uv run ruff check src/`: pass; `uv run mypy rag_backend/ --explicit-package-bases` from `backend/src`: 1,193 files pass.
- `check-integrity.sh backend`: 0 blockers, 0 warnings.
- `gates.sh backend:pip-audit`: PASS — "No known vulnerabilities found"; no ignore was added.

## QA Report

[AE-0566.qa.md](../reports/AE-0566.qa.md) — PASS after the dnspython extension (external QA had FAILed only on the then-out-of-scope dnspython advisory; the re-check validated the dnspython patch, the clean audit, and the unchanged no-`.feature` classification). PR CI pending.

## Decision Log

- 2026-10-27 (Pedro): raise the existing transitive floor to msgpack 1.2.3+ and keep the change limited to that package.
- 2026-10-27 (implementation): allow the lock resolver to select the latest compatible 1.2.3+ patch while rejecting unrelated upgrades through diff review.
- 2026-10-27 (Pedro): extend the same PR and ticket with an equivalent `dnspython>=2.9.0` transitive floor for CVE-2026-114605 rather than opening a second ticket, since the same gate and lockfile are affected.

## Blockers

None. The dnspython advisory is resolved in this ticket; PR CI must now run green on the single push.

## Final Summary

The msgpack floor is `>=1.2.3` (resolving 1.2.4, GHSA-6v7p-g79w-8964 and CVE-2026-114613 documented) and the dnspython floor is `>=2.9.0` (CVE-2026-114605 documented), with both lock updates minimal and revision 5 retained. `backend:pip-audit` passes with no findings, 45 targeted tests pass, Ruff, strict mypy, and integrity pass. External QA failed only on the then-out-of-scope dnspython advisory; the extension re-check passes and PR CI runs on the single push.
