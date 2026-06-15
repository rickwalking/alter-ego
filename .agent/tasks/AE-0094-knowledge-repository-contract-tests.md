# AE-0094 — Fake + PostgreSQL repository contract tests

Status: Ready
Tier: T2
Priority: Medium
Type: Tests
Area: Tests
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: test/ae-0094-repo-contract-tests
Kanban Card: TBD
Created: 2026-06-15
Updated: 2026-06-15

## Goal

Add a shared repository contract test suite exercised against BOTH a fake in-memory knowledge repository and the PostgreSQL implementation, so the port's behavior is pinned across adapters.

## Problem

There is no shared contract test ensuring the fake and Postgres repositories behave identically; the module pilot needs this to make adapter swaps safe and to model the reusable template.

## Scope

- Write one parametrized contract suite covering create/get/list/update/delete/count + owner-scoped queries + scope/is_public round-trip, run against a fake repo and `PostgresDocumentRepository`.
- Use SQLite/in-memory or a Postgres test fixture per existing conventions.
- Reference the AE-0088 behaviors where relevant.

## Non-Goals

- No production code change beyond a fake repo for tests.
- No new endpoints.

## Modularization Alignment (2026-06-15)

Phase 2 of the modularization plan (`.agent/reports/domain-modularization.options.md` §Phase 2). **Behavior-preserving extraction** — `/api/documents` and `/api/search` stay byte-identical; NO renames (Phase 4+). Builds on Phase 1 (PR #15): follow `docs/architecture/module-conventions.md` (AE-0081) + `modules/_template/`; satisfy the AE-0082 import contracts; compose via `bootstrap/` (no `get_container()` in module application code). Risk-register F1-F4 are Phase 4+ and do not apply (additive only). Establishes the contract-test pattern reused by later modules; runs in the existing pytest gates.

## Acceptance Criteria

- [ ] A shared contract suite SHALL run against BOTH a fake repo and PostgresDocumentRepository
- [ ] THE contract SHALL cover create/get/list/update/delete/count, owner-scoped queries, and scope/is_public round-trip
- [ ] WHEN the same contract runs against both adapters THE observable behavior SHALL match
- [ ] WHEN `uv run pytest` runs THE contract tests SHALL pass; mypy strict on the test + fake
- [ ] THE fake repository SHALL implement the DocumentRepository port (type-checked)

## Gherkin Scenarios

Not applicable — behavior-preserving extraction; no runtime behavior change (verified by the AE-0088 safety net).

## Delta

### ADDED

- shared repository contract test suite
- fake in-memory knowledge repository (test double)

### MODIFIED

- None

### REMOVED

- None

## Affected Areas

- Backend: test fake only
- Frontend: none
- Database: none
- API: none
- Tests: repository contract suite
- Docs: none
- Prompts/LLM: none
- Observability: none
- Deployment: none

## Dependencies

- Blocks: none
- Blocked by: AE-0089, AE-0090
- Related: AE-0088

## Implementation Plan

1. Write the parametrized contract suite.
2. Provide a fake repo implementing the port.
3. Run against fake + Postgres; mypy.

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
