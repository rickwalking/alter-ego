# AE-0096 — Phase 3 epic: Identity & Conversation boundaries

Status: Ready
Tier: T3
Priority: High
Type: Epic
Area: Cross-cutting
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: N/A (epic; sub-tickets carry branches)
Kanban Card: TBD
Created: 2026-06-15
Updated: 2026-06-15

## Goal

Extract `modules/identity/` (auth/admin/users/roles) and `modules/conversation/` (chat/messages/streaming) behind public facades, routes as thin adapters, chat-agent construction as an adapter behind conversation contracts — behavior-preserving. Tracks AE-0097 through AE-0103.

## Problem

Phase 2 proved the module pattern on Knowledge. Phase 3 applies it to two more contexts; auth/admin and conversation/streaming logic currently live in routes + dependencies with cross-cutting coupling.

## Scope

- Track AE-0097 (safety nets), AE-0098 (identity skeleton), AE-0099 (identity routes), AE-0100 (conversation skeleton + ChatAgentFactory), AE-0101 (conversation routes), AE-0102 (SSE streaming), AE-0103 (import contracts + exit gate).
- Enforce the phase exit gate. Order: A {0097,0098,0100} → B {0099,0101} → C {0102} → D {0103}.

## Non-Goals

- No renames (Phase 4+).
- No carousel extraction (Phase 4/5).
- No new access_control module (resource_access stays shared).

## Modularization Alignment (2026-06-15)

Phase 3 of the modularization plan (§Phase 3). **Behavior-preserving** — cookies (access_token/anon_token), HS256 JWT payloads, bcrypt, URLs, and SSE event payloads/keep-alive/Last-Event-ID/X-Agent-Origin stay byte-identical; NO renames (Phase 4+). Follow `docs/architecture/module-conventions.md` + `modules/_template`; reuse the Phase-2 `platform/database` UoW, the AE-0093 `KnowledgeSearchPort`, and the knowledge facade; compose via DI at the edge (no get_container in module code). `api/middleware/auth.py`, `infrastructure/auth.py`, and `api/dependencies/resource_access.py` stay at root (shared). Precondition: Phase 2 (PR #16) merged.

## Acceptance Criteria

- [ ] WHEN all of AE-0097-0103 reach Review with QA pass THE epic SHALL be complete
- [ ] THE API routes (auth/admin/conversations/chat_stream) SHALL be thin adapters delegating to facades
- [ ] THE conversation application code SHALL NOT import concrete Postgres repositories
- [ ] Identity persistence SHALL NOT be accessed directly by unrelated routes (via facade/shared deps)
- [ ] WHEN auth/admin/conversation endpoints + the SSE stream run THE responses (incl. cookies/JWT/SSE payloads) SHALL diff to ZERO against the AE-0097 pre-refactor snapshots

## Gherkin Scenarios

Not applicable — behavior-preserving extraction; no runtime behavior change (verified by the AE-0097 safety net).

## Delta

### ADDED

- None

### MODIFIED

- None

### REMOVED

- None

## Affected Areas

- Backend: two new modules
- Frontend: none
- Database: none
- API: unchanged contracts
- Tests: yes
- Docs: template examples
- Prompts/LLM: none
- Observability: none
- Deployment: no

## Dependencies

- Blocks: Phase 4 (EditorialProject facade) start
- Blocked by: Phase 2 (PR #16) merge
- Related: AE-0087 (Phase 2 epic)

## Implementation Plan

1. Drive Waves A-D per docs/plans/phase-3-identity-conversation.md.
2. architect validate loop → Ready.
3. Per-wave developer-skill + QA-guardian loop; keep safety nets green.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-15

Ticket created by planner (Phase 3 breakdown).

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
