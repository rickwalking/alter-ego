# AE-0486 — Chat: nobody but the owner (or an admin) reads or writes a signed-in user's conversation

Status: In Development
Tier: T1
Priority: High
Type: Bug
Area: Backend
Owner: Claude — /chat QA, CHAT-20
Branch: fix/ae-0486-chat-ownership
Created: 2026-10-22
Updated: 2026-10-22

## Goal

A conversation owned by a signed-in user is reachable only by its owner and by admins. Everyone else, signed in
or not, gets the same 404 an unknown id gets.

## Problem

Found by the /chat QA (CHAT-20). `POST /api/conversations/{id}/chat/stream` had no access check: any anonymous
client that knew the id streamed into a signed-in user's conversation, and both turns were persisted into the
owner's history (history pollution and LLM cost). The non-streaming `POST /{id}/chat` let anonymous callers through
the same way. Reads answered 403 to other users, which tells a caller the id exists.

## Scope (Pedro's decision, 2026-10-22)

- Anonymous callers never read or write a conversation owned by a signed-in user; the answer is 404, never 403.
- Same rule on every conversation endpoint: stream, non-stream chat, get, messages, generate-title, delete, and the
  carousel publish-chat stream. The list stays owner-filtered.
- Unknown ids on the stream now answer 404 before the stream starts (was 200 + an SSE `error` event), so an unknown
  id and a foreign id look identical.
- Anonymous conversations stay open to the anonymous stream (the public /chat flow).
- Admins keep access to signed-in users' conversations (unchanged).

## Non-Goals

- Binding anonymous conversations to their `anon_token` cookie.
- Any frontend change (the error copy is a separate /chat PR).

## Acceptance Criteria

- [x] Anonymous stream / chat into a signed-in user's conversation: 404, nothing persisted.
- [x] Another user on stream, chat, get, messages, generate-title, delete, publish-chat: 404 "Conversation not found".
- [x] Owner and admin keep 200 / 204; anonymous reads stay 401.
- [x] Unknown and foreign ids return the same 404 body on the stream.
- [x] Anonymous visitors still stream into anonymous conversations.

## Repro Steps

1. Sign in, open /dashboard/chat, note the conversation id.
2. Without cookies: `POST /api/conversations/<id>/chat/stream {"content":"hi"}`.
3. Before: 200 and both turns saved into the owner's conversation. After: 404.

## Affected Areas

- [x] Backend
- [ ] Frontend
- [x] Tests

## Dependencies

None.

## Progress Log

### 2026-10-22 10:20

Failing table-driven tests first (11 red: anon/other on stream and chat, other on get/messages/title/delete, unknown
vs foreign). Added `assert_conversation_writable` / `raise_conversation_not_found`; `assert_conversation_access`
now answers 404. Updated the three tests that pinned the old contract (unknown stream id → SSE error; anonymous
carousel chat → 403) and the two feature scenarios.

## Files Touched

- backend/src/rag_backend/api/dependencies/resource_access.py
- backend/src/rag_backend/api/routes/chat_stream.py, conversations.py
- backend/src/rag_backend/domain/constants/access_control.py (unused constant removed)
- backend/tests/features/conversation_ownership.feature (new), alter_ego_chat_sse.feature, publish_chat_sse.feature
- backend/tests/integration/test_conversation_ownership.py (new), test_chat_stream.py, test_api.py,
  test_identity_conversation_safety_net.py
- scripts/gherkin_refs_baseline.json (1 entry removed)
- docs/plan-sse-migration-v2.md (auth table)

## Test Evidence

Local backend gates, run one by one with `DATABASE_URL` on a local Postgres 16 (rebased on origin/main 583c3de42):
format, lint, lint-diff, blanket-ignore, strict-diff, type, imports, arch-ratchet, docstrings, dead-code,
inline-prompts, gherkin-refs, comments, blog-v1-dead-code, redis-factory, autopilot-env, healthcheck-loopback,
bandit, pip-audit, integrity, duplication, test (6567 passed, 2 skipped), diff-cover, migrations, schema-drift:
all PASS. Mutation: CI only (never run locally).

## QA Report

Pending.

## Blockers

None.
