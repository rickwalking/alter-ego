# AE-0092 — Move document routes behind application handlers (facade)

Status: Review
Tier: T2
Priority: High
Type: Task
Area: Backend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0092-document-handlers
Kanban Card: TBD
Created: 2026-06-15
Updated: 2026-06-15

## Goal

Move each `/api/documents` endpoint's logic behind a knowledge application command/query handler via the public facade, one endpoint at a time; routes become thin adapters. `/api/documents` stays byte-identical.

## Problem

Document routes today contain business logic and call `get_container()` directly. To complete the module they must delegate to application handlers behind the facade, with writes under the UoW.

## Scope

- For each endpoint (upload, create, list, get, status, delete, reprocess) add/route to a knowledge application handler invoked via `public.py`; routes only adapt HTTP <-> command/query.
- Resolve the knowledge facade at the HTTP edge (DI), not via `get_container()` inside handlers.
- Document writes go through the AE-0091 UoW as the SINGLE commit owner (routes no longer call .commit()).
- Preserve status codes, response schemas, access control exactly.

## Non-Goals

- No response/contract changes.
- No renames.
- No search changes (AE-0093).

## Modularization Alignment (2026-06-15)

Phase 2 of the modularization plan (`.agent/reports/domain-modularization.options.md` §Phase 2). **Behavior-preserving extraction** — `/api/documents` and `/api/search` stay byte-identical; NO renames (Phase 4+). Builds on Phase 1 (PR #15): follow `docs/architecture/module-conventions.md` (AE-0081) + `modules/_template/`; satisfy the AE-0082 import contracts; compose via `bootstrap/` (no `get_container()` in module application code). Risk-register F1-F4 are Phase 4+ and do not apply (additive only). Move endpoints one at a time, keeping AE-0088 green after each; the byte-identical guarantee is the gate.

## Acceptance Criteria

- [ ] EACH /api/documents endpoint SHALL delegate to a knowledge application handler via the public facade
- [ ] WHEN any /api/documents endpoint is called THE response SHALL diff to ZERO against the committed AE-0088 snapshots (merge gated on snapshot diff = 0)
- [ ] Knowledge document handlers SHALL NOT call `get_container()` (resolved via facade/DI at the edge)
- [ ] Document write endpoints SHALL persist via the AE-0091 UoW
- [ ] WHEN `uv run lint-imports` runs THE knowledge module SHALL stay contract-clean
- [ ] mypy strict + full suite + AE-0088 Gherkin green

## Gherkin Scenarios

```gherkin
Feature: Document endpoints unchanged after extraction

  Scenario: upload still returns 201 with the same shape
    Given a valid file upload
    When POST /api/documents/upload runs through the knowledge handler
    Then the response is 201 with the same DocumentUploadResponse shape
```

## Delta

### ADDED

- knowledge application command/query handlers for documents

### MODIFIED

- api/routes/documents.py (thin adapters via facade)

### REMOVED

- None

## Affected Areas

- Backend: handlers + routes
- Frontend: none
- Database: none
- API: unchanged contract
- Tests: endpoint parity
- Docs: none
- Prompts/LLM: none
- Observability: none
- Deployment: none

## Dependencies

- Blocks: AE-0095
- Blocked by: AE-0088 (snapshot safety net first), AE-0089, AE-0090, AE-0091
- Related: AE-0088

## Implementation Plan

1. Add document command/query handlers behind the facade.
2. Convert each route to delegate (one at a time).
3. Writes via UoW; keep responses identical; safety net green.

## QA Checklist

- [x] Security reviewed
- [x] Code quality reviewed
- [x] Acceptance criteria validated
- [x] Edge cases tested
- [x] Orphan/unfinished code checked

## Progress Log

### 2026-06-15

Ticket created by planner (Phase 2 breakdown).

## Files Touched

- api/routes/documents.py; api/dependencies/knowledge.py; modules/knowledge/*; domain/protocols/repositories.py; .importlinter

## Test Evidence

```
gates.sh backend: 13 PASS / 0 FAIL / 4 SKIP(DB); check-integrity: 0 net-new blockers
mypy 424; lint-imports 10/0; full suite 1757 passed; snapshot diff=0
```

## QA Report

✅ PASS — Phase 2 batch QA (gates.sh + check-integrity reproduced), 2 passes WARN→PASS. See `.agent/reports/AE-0092.qa.md` -> `.agent/reports/phase-2.qa.md`.

## Decision Log

Pending.

## Blockers

None.

## Final Summary

Pending.
