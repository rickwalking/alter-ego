# AE-0280 — alembic migration postgres-portability gate

Status: Intake
Tier: T2
Priority: P2
Type: Quality
Area: backend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-25
Updated: 2026-06-25

## Goal

A static gate that fails when an Alembic migration under
`backend/alembic/versions/*` uses postgres-specific constructs that diverge from
the project's sqlite-portable model types — specifically `postgresql.JSONB`,
`postgresql.JSON`, `postgresql.UUID`, and the `sa.false()` / `sa.true()` server
defaults. Catches the drift at lint time, before the CI migrations gate goes red
mid-PR.

## Problem

(Kaizen failure class C3 — migration portability drift.)
The models use SQLite-portable generic types (`sa.JSON`, `sa.Uuid`), but
autogenerate sometimes emits postgres-specific types. In PR #64 (AE-0269) the
migrations/schema-drift gate went red because the migration used
`postgresql` JSONB/UUID + `sa.false()` while the model used generics — the fix
was switching to `sa.JSON`/`sa.Uuid` + `server_default=sa.text('false')`
(commit 2717d263). The existing `gate_backend_migrations` detects model↔migration
*divergence* and `gate_backend_schema_drift` detects applied-migration gaps, but
neither flags the postgres-specific *type* that is the root cause — so the
failure only surfaces as a confusing autogenerate-diff red, late in CI.

A live audit (2026-06-25) found **4 pre-existing committed violations** already
in the tree:
- `alembic/versions/63eaefa67b8c_initial_baseline_schema.py:118,244,245`
  (`postgresql.JSON(astext_type=...)`)
- `alembic/versions/a1b2c3d4e5f6_add_documents_scope_is_public.py:41`
  (`server_default=sa.false()`)

No lint rule, ruff config, or `check-integrity.sh` pattern flags these today.

Source: `.agent/reports/kaizen-session-2026-06-25.plan.md` (proposal P2),
learnings record 10, memory `prod-db-schema-drift`.

## Scope

- A grep/AST check over `backend/alembic/versions/*.py` flagging
  `postgresql.JSONB`, `postgresql.JSON`, `postgresql.UUID`, `sa.false(`,
  `sa.true(`. Implement as either a `scripts/ci/check-integrity.sh` pattern
  (preferred — diff-scoped, mirrors existing categories) or a small dedicated
  gate in `scripts/ci/gates.sh`.
- Rule-fires regression test (AE-0180): seed a migration line with
  `postgresql.JSONB` → assert non-zero exit / blocker.
- Decide the 4 pre-existing violations: either fix them to the portable
  equivalents (`sa.JSON`, `sa.text('false')`) or grandfather with a documented
  `# integrity-ok: <reason>` marker. Prefer fixing where safe.

## Non-Goals

- Replacing the existing migrations / schema-drift gates — this complements them
  by catching the type-portability root cause earlier.
- Banning postgres types in non-migration code (the models are already generic by
  convention; this gate targets `alembic/versions/` only).

## Acceptance Criteria

- [ ] A check flags `postgresql.JSONB|postgresql.JSON|postgresql.UUID|sa.false(|sa.true(`
      in `backend/alembic/versions/*` and is wired into the gate set
      (`check-integrity.sh` or `gates.sh backend`).
- [ ] The check FAILS on a seeded violation — proven by a rule-fires test
      (AE-0180), asserting non-zero exit / blocker.
- [ ] The 4 pre-existing violations are fixed (portable equivalents) or
      grandfathered with a documented `integrity-ok:` reason; the gate is green
      on HEAD.
- [ ] `docs/guides/qa-checkpoints.md` documents the rule.

## Gherkin Scenarios

```gherkin
Feature: migration postgres-portability gate

  Scenario: a postgres-specific JSONB column is flagged
    Given a new migration declaring postgresql.JSONB on a column
    When the portability check runs over alembic/versions
    Then it reports a blocker naming the file and the non-portable type

  Scenario: a sa.false() server default is flagged
    Given a migration with server_default=sa.false()
    When the portability check runs
    Then it reports a blocker and suggests sa.text('false')

  Scenario: a portable migration passes
    Given a migration using sa.JSON and sa.Uuid only
    When the portability check runs
    Then it reports no blockers
```

## Delta

### ADDED

- portability check (pattern in `check-integrity.sh` or new `gates.sh` gate)
- rule-fires regression test

### MODIFIED

- `scripts/ci/check-integrity.sh` or `scripts/ci/gates.sh`
- the 2 migration files with pre-existing violations (or `integrity-ok` markers)
- `docs/guides/qa-checkpoints.md`

### REMOVED

- (none)

## Affected Areas

- Backend: alembic migrations + the integrity/gate harness
- Frontend: none
- Database: no schema change (lint-only)
- API: none
- Tests: rule-fires test
- Docs: qa-checkpoints.md
- Prompts/LLM: none
- Observability: none
- Deployment: none (CI gate)

## Dependencies

- Blocks:
- Blocked by:
- Related: AE-0269 (the PR that hit this), memory `prod-db-schema-drift`

## Implementation Plan

1. Add the grep pattern(s) to `check-integrity.sh` (preferred) with a clear
   remediation message (portable equivalents).
2. Add the rule-fires test seeding a postgres-specific type.
3. Resolve the 4 existing violations (fix or grandfather with reason).
4. Document in qa-checkpoints.md; confirm `gates.sh backend:integrity` green.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-25 HH:mm

Ticket created.

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Decision Log

Pending.

## Blockers

None.

## Final Summary

Pending.
