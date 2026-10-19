# AE-0432 — ai-suggest / ai-improve merge metadata onto the latest row

Status: Dev Complete
Tier: T1
Priority: P1
Type: Bug
Area: Backend
Owner: Claude (worker)
Agent Lane: developer → qa → release
Branch: feat/ae-0432-ai-suggest-metadata-merge
Kanban Card: TBD
Created: 2026-10-19
Updated: 2026-10-19

## Goal

ai-suggest and ai-improve must not erase `ai_generation_metadata` (image budget reservations,
recorded AI actions) or `ai_suggestions` committed by other requests during their LLM call.

## Problem

`api/routes/blog_post_ai.py` loads the post before the LLM call and, after it, writes back a full
copy of that stale `ai_generation_metadata` (`_record_ai_action`) and `ai_suggestions`. An image
budget reservation (AE-0424 `reserve_image_budget`) or an AE-0425 batch reservation committed
during the call is erased: the per-post image cap undercounts and recorded AI actions are lost.
Found in the orchestrator review of PR #147.

## Scope

- Release the read transaction before the LLM call; afterwards re-read the row with
  `lock_blog_post` (`SELECT ... FOR UPDATE`) and apply the AI action / suggestion onto the
  LATEST metadata and suggestions (same pattern as the AE-0424 slot writes).
- Optional hardening: the budget reservation's in-process `asyncio.Lock` becomes per post
  (posts no longer serialize each other within a worker).

## Non-Goals

- No API shape change; no change to the slot-write routes.

## Acceptance Criteria

- [x] AC1: A reservation committed during ai-suggest survives (`blog_image_generations` keeps it)
      and the suggest action is recorded on top of actions recorded meanwhile.
- [x] AC2: Same for ai-improve.
- [x] AC3: A suggestion stored by a concurrent ai-suggest is kept.
- [x] AC4: Reservation locks are per post (one post's reservation does not block another's).

## Gherkin Scenarios

- `backend/tests/features/blog_ai_metadata_merge_ae0432.feature`

## Affected Areas

- Backend: `api/routes/blog_post_ai.py`, `api/dependencies/blog_image_budget.py`
- Tests: backend integration

## Dependencies

- Blocked by: AE-0424 (merged into the AE-0423 branch). Related: AE-0425 (batch reservations).

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-10-19

Ticket created from the orchestrator follow-up on PR #147.

## Files Touched

- `backend/src/rag_backend/api/routes/blog_post_ai.py` — `_authorize_then_release` (access
  check, then end the read transaction before the LLM call); after the call the row is
  re-read with `lock_blog_post` and the suggestion / AI action are merged onto it.
- `backend/src/rag_backend/api/dependencies/blog_image_budget.py` — reservation lock per post.
- `backend/tests/features/blog_ai_metadata_merge_ae0432.feature`,
  `backend/tests/integration/test_blog_ai_metadata_merge_ae0432.py`.

## Test Evidence

- New tests (4): reservation during ai-suggest / ai-improve kept, concurrent suggestion kept,
  per-post reservation locks. The 3 merge tests FAIL on the pre-fix route and pass with it.
- Targeted suites: 131 passed (incl. AE-0424 editor routes, ai-service unit + mutation suites,
  publishing safety net, phase-3 workflow, route snapshot).
- `gates.sh backend --changed-only`: 17/17 PASS. Test, diff-cover, migrations, schema-drift and
  mutation run in CI (orchestrator rule 2026-10-19: no local mutation runs).

## QA Report

Pending.

## Decision Log

- Release the read transaction before the LLM call (no connection held for seconds; matches
  the AE-0424 slot routes) and merge after it under `FOR UPDATE`, instead of an optimistic
  `lock_version` check: suggest/improve are not content writes and must not 409 the editor.
- The reservation lock is keyed per post (and per event loop); the row lock stays the
  cross-process guarantee.

## Risk & Size

- **Risk:** Low — narrow route change with tests.
- **Size:** S

## Blockers

None.

## Final Summary

Pending.
