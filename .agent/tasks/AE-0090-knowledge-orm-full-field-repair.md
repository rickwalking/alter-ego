# AE-0090 — Repair full-field ORM mapping (scope/is_public) + additive migration

Status: Ready
Tier: T2
Priority: High
Type: Task
Area: Backend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0090-orm-full-field-repair
Kanban Card: TBD
Created: 2026-06-15
Updated: 2026-06-15

## Goal

Map `scope` (DocumentScope) and `is_public` (bool) on `DocumentModel` (currently unmapped though the `Document` entity has them) and add an additive Alembic migration on top of the squashed baseline.

## Problem

The `Document` entity carries `scope`/`is_public` but `DocumentModel` and the AE-0086 squashed baseline do not persist them, so those fields are silently dropped on round-trip. The plan calls this out as 'repair full-field ORM mappings.'

## Scope

- Add `scope` + `is_public` columns to `DocumentModel` with full `to_entity`/`from_entity`/`update_from_entity` mapping.
- Add an additive Alembic migration (`down_revision = 63eaefa67b8c`): `scope` `String(20)` `server_default='personal'` NOT NULL, `is_public` `Boolean` `server_default=false` NOT NULL (data-preserving backfill).
- Keep the schema equal to `Base.metadata` so the AE-0084 empty-autogenerate-diff drift check passes.
- Document the existing-dev-DB path (upgrade head).

## Non-Goals

- No renames or type reshapes (additive only).
- No drain-before-migrate ceremony (additive nullable, pre-production — not a Phase 4+ reshape).

## Modularization Alignment (2026-06-15)

Phase 2 of the modularization plan (`.agent/reports/domain-modularization.options.md` §Phase 2). **Behavior-preserving extraction** — `/api/documents` and `/api/search` stay byte-identical; NO renames (Phase 4+). Builds on Phase 1 (PR #15): follow `docs/architecture/module-conventions.md` (AE-0081) + `modules/_template/`; satisfy the AE-0082 import contracts; compose via `bootstrap/` (no `get_container()` in module application code). Risk-register F1-F4 are Phase 4+ and do not apply (additive only). Additive migration chains on AE-0086's baseline; must keep AE-0084's fresh-DB upgrade + empty-diff green.

## Acceptance Criteria

- [ ] THE `DocumentModel` SHALL map `scope` and `is_public` with full to/from-entity round-trip (no field dropped)
- [ ] THE additive migration SHALL have `down_revision = 63eaefa67b8c` and add the columns data-preservingly
- [ ] WHEN `alembic upgrade head` runs on a fresh DB THE schema SHALL match `Base.metadata` (AE-0084 empty autogenerate diff)
- [ ] WHEN `alembic upgrade head` then `downgrade` runs THE round-trip SHALL succeed
- [ ] WHEN a document with non-default scope/is_public is saved and reloaded THE values SHALL persist (test)
- [ ] WHEN `uv run pytest` + `mypy` run THE suite + types SHALL pass

## Gherkin Scenarios

```gherkin
Feature: Full-field document persistence

  Scenario: scope and is_public round-trip
    Given a document with scope INTERNAL and is_public false
    When it is saved and reloaded from the repository
    Then scope is INTERNAL and is_public is false
```

## Delta

### ADDED

- Alembic additive migration (down_revision=63eaefa67b8c)
- persistence test for scope/is_public

### MODIFIED

- infrastructure/database/models/document.py (map scope/is_public)

### REMOVED

- None

## Affected Areas

- Backend: ORM model
- Frontend: none
- Database: additive columns
- API: none
- Tests: round-trip persistence
- Docs: none
- Prompts/LLM: none
- Observability: none
- Deployment: none

## Dependencies

- Blocks: AE-0092, AE-0094
- Blocked by: none
- Related: AE-0086, AE-0089

## Implementation Plan

1. Map scope/is_public on DocumentModel + to/from entity.
2. Author additive migration on the baseline.
3. Verify fresh-DB upgrade + empty diff + round-trip; persistence test.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-15

Ticket created by planner (Phase 2 breakdown).

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
