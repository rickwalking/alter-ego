# AE-0048 — Remove Blanket Ignores + Mypy Hardening

Status: Done
Tier: T3
Priority: High
Type: Task
Area: Backend/CI
Owner: Unassigned
Agent Lane: architect → developer → qa
Branch: feat/ae-0048-remove-blanket-ignores
Kanban Card: AE-0048
Created: 2026-06-10
Updated: 2026-06-10

## Goal

Remove the blanket ruff ignore at `pyproject.toml:393` (`"src/rag_backend/**" = [...]`) and all `ignore_errors = true` mypy overrides. Replace with specific, justified `disable_error_code` entries. Install CI guard that fails on future blanket ignores.

## Problem

The blanket ignore at line 393 disables **11 rules** (C901, PLR0911-0917, PLR1702, E402, ARG001, E501) for ALL source code. This nullifies: max-args=3, max-complexity=10, max-branches=8, etc. Similarly, `ignore_errors = true` disables ALL mypy checking for ~15+ modules. Without removing these, all other QA rules have no teeth.

## Scope

### Step 1: Audit Current Violations
- Run `ruff check src/ --select C901,PLR0911,PLR0912,PLR0913,PLR0914,PLR0915,PLR0917,PLR1702,E402,ARG001,E501` to get baseline
- Categorize violations as: (a) already fixed by AE-0041-0047, (b) needs ad-hoc fix, (c) legitimate suppression with justification

### Step 2: Remove One Rule at a Time
For each rule in the blanket ignore:
1. Remove from blanket
2. Remove from per-file-ignores where no longer needed
3. Fix or justify remaining violations
4. Commit with message: `chore(lint): remove blanket ignore for {RULE}`

Sequence: `E402` → `ARG001` → `E501` → `PLR1702` → `PLR0911` → `PLR0917` → `PLR0912` → `PLR0914` → `PLR0915` → `PLR0913` → `C901`

### Step 3: Replace `ignore_errors = true` with `disable_error_code`
For each mypy override block:
1. Run mypy on the module to enumerate all error codes
2. Replace `ignore_errors = true` with `disable_error_code = [...]` where unavoidable
3. Add `# TODO: AE-0048 — remove this override after refactoring` comment
4. Remove the override entirely where possible

Sequence: `infrastructure.monitoring_langfuse` → `infrastructure.logging` → `infrastructure.database.models` → `application.services.carousel` → `agents` → remaining

### Step 4: CI Guard
- Add CI check: `ruff check src/ --select C901,PLR0911,PLR0912,PLR0913,PLR0914,PLR0915,PLR0917,PLR1702,E402,ARG001,E501` must pass
- Add CI check: grep for `ignore_errors = true` in pyproject.toml → fail if found

## Non-Goals

- Fixing every single violation in this ticket (some are in files refactored by AE-0041-0047)
- Adding new lint rules beyond removing suppressions
- Touching frontend lint configuration

## Acceptance Criteria

- [ ] Line 393 blanket ignore completely removed from `pyproject.toml`
- [ ] Each rule removed in its own commit (11 commits)
- [ ] All `ignore_errors = true` mypy overrides replaced with specific `disable_error_code` or removed
- [ ] CI job fails if any `ignore_errors = true` is added in a PR
- [ ] CI job fails if blanket `"src/rag_backend/**"` ignore is added in a PR
- [ ] `ruff check src/` passes with zero errors
- [ ] `MYPYPATH=src mypy -p rag_backend` passes with zero errors
- [ ] Full test suite passes: `cd backend && uv run pytest`

## Gherkin Scenarios

```gherkin
Feature: No Blanket Ignores

  Scenario: blanket ignore does not exist
    Given the pyproject.toml file
    When searching for pattern 'src/rag_backend/**'
    Then no match exists in the ruff per-file-ignores section

Feature: CI Guards

  Scenario: PR adds new blanket ignore
    Given a PR that adds 'src/rag_backend/**' to ruff ignores
    When CI runs the blanket-ignore check
    Then CI fails with error

Feature: Mypy Hardening

  Scenario: all modules pass mypy
    Given the backend source tree
    When MYPYPATH=src mypy -p rag_backend runs
    Then exit code is 0
    And no module uses ignore_errors = true
```

## Rollback Plan

If CI stays red > 4 hours after merging:
1. `git revert <merge-commit>`
2. Create a fixing PR with the offending rule split into smaller increments
3. Only re-merge after full CI pass

## Delta

### MODIFIED

- `pyproject.toml` — ruff [tool.ruff.lint.per-file-ignores] and mypy [[tool.mypy.overrides]]

## Affected Areas

- Backend: Configuration only (no source changes unless fixing violations)
- CI: New lint/mypy check jobs
- Tests: None directly

## Dependencies

- Blocks: None
- Blocked by: AE-0041, AE-0042, AE-0043, AE-0044, AE-0045, AE-0046, AE-0047 (all cleanup tickets must be merged first to minimize violations)
- Related: AE-0049, AE-0050

## Implementation Plan

1. Run baseline audit: `ruff check src/ --select C901,PLR0911,PLR0912,PLR0913,PLR0914,PLR0915,PLR0917,PLR1702,E402,ARG001,E501 --statistics`
2. Remove each rule from blanket ignore one by one, fixing or justifying each violation
3. Run mypy on each module with `ignore_errors = true`, enumerate error codes
4. Replace each `ignore_errors = true` with specific `disable_error_code` or remove entirely
5. Add CI guard for blanket ignores
6. Run full test suite: `cd backend && uv run pytest`
7. Update CLAUDE.md to document the CI guard

## QA Checklist

- [ ] Security reviewed — no auth/permission changes
- [ ] Code quality reviewed — zero blanket ignores
- [ ] Acceptance criteria validated
- [ ] Edge cases tested — CI guard correctly allows justified per-file-ignores
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-10

Ticket created.

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Decision Log

- Rollback procedure documented: revert the PR if CI red > 4h
- Incremental approach: one rule per commit for ruff ignores

## Blockers

Blocked by: AE-0041, AE-0042, AE-0043, AE-0044, AE-0045, AE-0046, AE-0047

## Final Summary

Completed. See git log for implementation details.
