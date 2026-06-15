# AE-0097 — Identity + Conversation Gherkin safety nets + response/SSE snapshots

Status: Dev Complete
Tier: T2
Priority: High
Type: Tests
Area: Tests
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: test/ae-0097-id-conv-safety-net
Kanban Card: TBD
Created: 2026-06-15
Updated: 2026-06-15

## Goal

Build the byte-identical safety net for both contexts before any refactor: audit/extend auth, admin, and conversation Gherkin, and capture committed response + SSE-stream snapshots (cookies, JWT shape, event sequence, keep-alive, headers).

## Problem

Phase 3 moves auth/admin/conversation/streaming behind facades; without an enforceable byte-identical baseline the refactor can silently change cookies, token payloads, or SSE framing.

## Scope

- Audit/extend `auth.feature`, `admin.feature`, `conversations.feature` (+ any chat/anonymous_chat) for login/logout/me/change-password, admin user CRUD + role assignment, conversation CRUD + non-stream chat + generate-title.
- Capture committed response snapshots for /api auth/admin/conversations endpoints — INCLUDING Set-Cookie attributes (access_token, anon_token: httponly/secure/samesite/max_age) and headers (X-Agent-Origin).
- Capture an SSE-stream snapshot for both chat/stream endpoints USING A DETERMINISTIC MOCK/STUB AGENT (fixed token sequence — LLM content/event-ids/keep-alive timing are non-deterministic, so do NOT byte-diff a live stream): assert event TYPES in order (token/sources/complete/error/tool_result), the `id:`/`data:` framing FORMAT, and Last-Event-ID resume — extract events and ignore keep-alive interleaving (or cap keep-alive after mock output). HTTP responses + cookies (access_token/anon_token attrs) + JWT shape ARE deterministic and remain a true byte-identical snapshot.
- Record a green baseline; each scenario backed by an executing test.

## Non-Goals

- No production code change.

## Modularization Alignment (2026-06-15)

Phase 3 of the modularization plan (§Phase 3). **Behavior-preserving** — cookies (access_token/anon_token), HS256 JWT payloads, bcrypt, URLs, and SSE event payloads/keep-alive/Last-Event-ID/X-Agent-Origin stay byte-identical; NO renames (Phase 4+). Follow `docs/architecture/module-conventions.md` + `modules/_template`; reuse the Phase-2 `platform/database` UoW, the AE-0093 `KnowledgeSearchPort`, and the knowledge facade; compose via DI at the edge (no get_container in module code). `api/middleware/auth.py`, `infrastructure/auth.py`, and `api/dependencies/resource_access.py` stay at root (shared). Precondition: Phase 2 (PR #16) merged. This is the gate AE-0099/0101/0102 diff against (snapshot diff=0).

## Acceptance Criteria

- [ ] THE auth/admin/conversation Gherkin SHALL cover login/logout/me/change-password, admin user CRUD + role assignment, conversation CRUD + non-stream chat
- [ ] THE committed snapshots SHALL capture every relevant /api response INCLUDING Set-Cookie attributes (access_token, anon_token) and X-Agent-Origin, with a diff helper
- [ ] THE SSE-stream snapshot SHALL be captured via a DETERMINISTIC mock agent and assert event TYPES in order + `id:`/`data:` framing FORMAT + Last-Event-ID resume (NOT a raw byte diff of LLM content; keep-alive interleaving ignored) — falsifiable by a reordered/renamed event
- [ ] THE HTTP response + cookie (access_token/anon_token attributes) + HS256 JWT-shape snapshots SHALL be true byte-identical (deterministic) baselines
- [ ] EACH added scenario SHALL be backed by an executing test (no orphan scenarios)
- [ ] WHEN `uv run pytest` runs THE safety-net suite SHALL pass with NO production code modified (green baseline recorded)

## Gherkin Scenarios

```gherkin
Feature: Identity/Conversation safety net (representative)

  Scenario: login sets the access_token cookie unchanged
    Given valid credentials
    When POST /api/auth/token runs
    Then the response sets access_token (httponly, secure, samesite=strict) and an HS256 JWT

  Scenario: chat stream emits the same SSE event sequence
    Given a conversation
    When POST /api/conversations/{id}/chat/stream runs
    Then the SSE events (token/sources/complete) and keep-alive framing match the snapshot
```

## Delta

### ADDED

- auth/admin/conversation scenarios + backing tests
- response + SSE snapshots + diff helper (tests/snapshots/identity, tests/snapshots/conversation)

### MODIFIED

- tests/features/{auth,admin,conversations}.feature

### REMOVED

- None

## Affected Areas

- Backend: none
- Frontend: none
- Database: none
- API: none
- Tests: safety nets + snapshots
- Docs: none
- Prompts/LLM: none
- Observability: none
- Deployment: none

## Dependencies

- Blocks: AE-0099, AE-0101, AE-0102
- Blocked by: none
- Related: AE-0098, AE-0100

## Implementation Plan

1. Audit existing scenarios vs live behavior; add gaps.
2. Capture response + SSE snapshots (cookies/headers/framing).
3. Record green baseline.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-15

Ticket created by planner (Phase 3 breakdown).

Dev Complete (Wave A). Implemented byte-identical safety net: 46 tests green (HTTP+cookie+JWT byte-identical snapshots; SSE asserted via deterministic mock agent — event types/order + id:/data: framing + Last-Event-ID, keep-alive ignored). No src/ changed. Gate spine 14 PASS/0 FAIL/3 SKIP(DB→CI), integrity 0 blockers, mypy/lint-imports green.

## Files Touched

backend/tests/integration/test_identity_conversation_safety_net.py, tests/snapshots/identity/*, tests/snapshots/conversation/*, tests/features/{auth,admin,conversations}.feature

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
