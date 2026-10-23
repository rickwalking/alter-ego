# AE-0534 — A rolled-back scope change or reprocess leaves the document retryable

Status: In Development
Tier: T1
Priority: Medium
Type: Bug
Area: Backend
Owner: Claude Code (claude-opus-5-5)
Branch: fix/ae-0534-knowledge-rescope-rollback
Created: 2026-10-23
Updated: 2026-10-23

## Goal

When a scope change or a reprocess fails after the document's chunks were deleted (the commit included),
the document shows as failed with Retry instead of a completed document with no vectors, and the request
fails with its own error.

## Problem

Review of the document-scope PR (AE-0502). `KnowledgeService.change_scope` deletes the chunks from the old
namespace, re-indexes into the new one and commits. When the commit fails, the rollback drops the
new-namespace chunks but the old-namespace chunks are already gone, so the row rolls back to COMPLETED in
the old scope with no vectors and the Knowledge Base offers no Retry. A reprocess has the same gap. If the
chunk cleanup itself raises inside the error handler, its error replaces the original one. The 409
system-scope check ran in the route before the row lock, on an unlocked read.

## Scope

- On a failed scope change: drop the new namespace's chunks, then save the document FAILED
  (`processing_error`, 0 chunks) in a fresh transaction, and raise the original error.
- On a failed reprocess: save the document FAILED the same way and raise the original error.
- A failing cleanup step (chunk drop or the FAILED save) is logged and never replaces the original error.
- The system-scope check runs in the service after `SELECT ... FOR UPDATE`; the route maps
  `SystemScopeError` to 409.

## Non-Goals

- Re-indexing into the old namespace on rollback (Retry does that, on the owner's click).
- Frontend changes: a failed document already shows its reason and Retry.

## Acceptance Criteria

- [x] Given a scope change whose commit fails, Then the new namespace's chunks are deleted, the document is
      saved FAILED with `processing_error` and 0 chunks, and the request raises the commit error.
- [x] Given a reprocess whose commit fails, Then the document is saved FAILED and the commit error is raised.
- [x] Given the chunk drop or the FAILED save raising during that cleanup, Then it is logged and the original
      error is raised.
- [x] Given a document in a system scope, Then the scope is checked after the row lock, the change is refused
      (409 on the route) and no chunk is touched.

## Gherkin Scenarios

- `backend/tests/features/knowledge_reindex_recovery_ae0534.feature`

## Affected Areas

- Backend: `modules/knowledge/application/service.py`, new `application/reindex_recovery.py`, new
  `domain/scopes.py` (selectable scopes + `SystemScopeError`), facade exports, `api/routes/document_scope.py`.
- Frontend: none. Database: none. API: none (409 stays).
- Tests: backend unit; the AE-0502 integration tests cover the 409 route.

## Dependencies

- Blocked by: AE-0502 (merged, #251).
- Blocks: none.

## Progress Log

### 2026-10-23

Ticket written from Pedro's review of the AE-0502 PR. Implemented with `ReindexRecovery` (chunk drop + FAILED
save in a fresh transaction after a rollback, both logged on failure) and the system-scope check moved under
the lock.

## Files Touched

- backend: `modules/knowledge/application/{service.py,reindex_recovery.py}`, `modules/knowledge/domain/scopes.py`,
  `modules/knowledge/{__init__.py,public.py}`, `api/routes/document_scope.py`; tests
  `tests/unit/modules/knowledge/test_reindex_recovery_ae0534.py`, feature.

## Test Evidence

6 new unit tests green; the 14 knowledge test files (157 tests) green. Gates:
`.agent/reports/AE-0534.dev-summary.md`.

## QA Report

Pending.

## Blockers

None.
