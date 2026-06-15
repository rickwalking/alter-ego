# AE-0088 — Document + search Gherkin safety net (audit & extend)

Status: Ready
Tier: T2
Priority: High
Type: Tests
Area: Tests
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: test/ae-0088-knowledge-gherkin
Kanban Card: TBD
Created: 2026-06-15
Updated: 2026-06-15

## Goal

Audit and extend the existing `documents.feature` (20) and `search.feature` (11) Gherkin so they form a complete behavioral safety net for the Knowledge extraction, then record a green baseline run.

## Problem

The Phase 2 spec assumed no document/search Gherkin existed; in fact both files exist. Before relocating code, the scenarios must cover the behaviors the refactor must preserve (CRUD/upload/reprocess/status, hybrid search, scope/access-control, error paths) so each later slice can be checked against them.

## Scope

- Review `backend/tests/features/documents.feature` + `search.feature` against the live `/api/documents` and `/api/search` behavior; list coverage gaps.
- Add scenarios for: document scope (PERSONAL/PUBLIC/CAROUSEL/INTERNAL) + `is_public` access control, owner-vs-admin listing, not-found/validation/permission error paths, hybrid-search alpha/top_k bounds.
- Ensure the .feature scenarios are backed by executing tests (reference scenario in test comments).
- Record a green baseline run as the pre-refactor reference.

## Non-Goals

- No production code change.
- No new endpoints.

## Modularization Alignment (2026-06-15)

Phase 2 of the modularization plan (`.agent/reports/domain-modularization.options.md` §Phase 2). **Behavior-preserving extraction** — `/api/documents` and `/api/search` stay byte-identical; NO renames (Phase 4+). Builds on Phase 1 (PR #15): follow `docs/architecture/module-conventions.md` (AE-0081) + `modules/_template/`; satisfy the AE-0082 import contracts; compose via `bootstrap/` (no `get_container()` in module application code). Risk-register F1-F4 are Phase 4+ and do not apply (additive only). This is the safety net every later Phase 2 slice must keep green; it encodes the byte-identical-API guarantee.

## Acceptance Criteria

- [ ] THE documents.feature and search.feature SHALL cover CRUD/upload/reprocess/status, hybrid search, scope/is_public access control, and error paths (gaps from the audit added)
- [ ] WHEN the document+search test suite runs on current (pre-refactor) code THE scenarios SHALL pass (green baseline recorded in Test Evidence)
- [ ] EACH added scenario SHALL be backed by an executing test referencing it (no orphan scenarios)
- [ ] THE scenarios SHALL assert the /api/documents and /api/search status codes + response shape (the contract later slices must preserve)
- [ ] WHEN `uv run pytest` runs the knowledge feature tests THE suite SHALL pass with no production code modified

## Gherkin Scenarios

```gherkin
Feature: Knowledge safety net (representative additions)

  Scenario: non-owner cannot read a private document
    Given a document owned by another user with is_public false
    When the user GETs /api/documents/{id}
    Then the API returns 403 or 404 per current behavior

  Scenario: hybrid search rejects out-of-range alpha
    Given a search request with alpha greater than 1
    When POST /api/search runs
    Then the API returns a 422 validation error
```

## Delta

### ADDED

- new scenarios in documents.feature / search.feature
- backing tests for added scenarios

### MODIFIED

- backend/tests/features/documents.feature
- backend/tests/features/search.feature

### REMOVED

- None

## Affected Areas

- Backend: none
- Frontend: none
- Database: none
- API: none
- Tests: document+search Gherkin + tests
- Docs: none
- Prompts/LLM: none
- Observability: none
- Deployment: none

## Dependencies

- Blocks: AE-0092, AE-0093 (safety net for the refactor)
- Blocked by: none
- Related: AE-0089

## Implementation Plan

1. Audit existing scenarios vs live behavior.
2. Add scope/access-control/error scenarios + backing tests.
3. Run and record the green baseline.

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
