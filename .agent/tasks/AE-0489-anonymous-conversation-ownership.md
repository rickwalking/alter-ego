# AE-0489 — Chat: an anonymous conversation accepts writes only from the visitor holding its anon_token

Status: In Development
Tier: T1
Priority: High
Type: Bug
Area: Backend
Owner: Claude — /chat QA follow-up to AE-0486 (review of #227)
Branch: fix/ae-0486-anon-ownership
Created: 2026-10-22
Updated: 2026-10-22

## Goal

Only the visitor who created an anonymous conversation can write into it, for as long as their page is open.

## Problem

`create_conversation` sets a signed `anon_token` cookie naming the new conversation (`conversation_id` claim), but
nothing verified it (`get_anonymous_payload` was unused). Anyone who knew an anonymous conversation's id could write
into it via `/chat/stream` or `/chat`, and read its history back through the agent. Signed-in users could write into
anonymous conversations too.

## Scope (Pedro's decision, 2026-10-22)

- When `conversation.user_id` is None, `assert_conversation_writable` requires a valid anon_token whose
  `conversation_id` claim matches; otherwise the same 404 as an unknown id. Applies to the stream, the non-stream
  chat and the publish-chat (an anonymous carousel conversation is now a 404 instead of a 403).
- New `ConversationCaller` (signed-in user + the conversations named by the visitor's valid `anon_token` cookies)
  resolved by `get_conversation_caller`. Only the HttpOnly cookie counts (a `?token=` URL parameter is ignored: it
  would leak through access logs and referrers).
- The token cookie is scoped to its conversation (`Path=/api/conversations/<id>`), so a second tab or New chat no
  longer overwrites the token of a conversation still open; every `anon_token` in the Cookie header is read, so a
  leftover site-wide token from before this change does not hide the scoped one.
- Reads of anonymous conversations were already closed (they need a signed-in owner).
- "Messages are not saved after refresh" stays by design; the cookie (`Path=/api/conversations/<id>`,
  `SameSite=Strict`, HttpOnly, 60 min) covers a page's lifetime.
- Pedro's decision (review of #239): a HARD 60-minute limit for anonymous conversations, no renewal. After it the
  stream answers 404; the chat errors PR (AE-0510) shows a friendly "start a new chat" message for it.
- The unused `get_anonymous_payload` (which also accepted a URL token) is removed.

## Non-Goals

- Refreshing the anon token past 60 minutes (Pedro: hard limit).

## Acceptance Criteria

- [x] The creating visitor keeps chatting (stream and chat).
- [x] Visitor B (own token) → 404 on visitor A's conversation; nothing saved.
- [x] A signed-in user without the token → 404.
- [x] Missing, expired, tampered (foreign-key) or URL-parameter token → 404, nothing saved.
- [x] Two conversations in one browser stay writable.

## Repro Steps

1. Open /chat in browser A, send a message, note the conversation id.
2. From another browser (or curl without cookies) `POST /api/conversations/<id>/chat/stream`.
3. Before: 200 and the message lands in A's conversation. After: 404.

## Affected Areas

- [x] Backend
- [ ] Frontend
- [x] Tests

## Dependencies

AE-0486 (#227, merged).

## Progress Log

### 2026-10-22 14:30

Failing tests first: 6 of 8 new cases failed on the AE-0486 branch. The fix is above. Test clients that stream as a
visitor now use `https://test` so the secure cookie is sent back (production is HTTPS). The shared fixtures moved to
`tests/integration/conversation_access_support.py`.

## Files Touched

- backend/src/rag_backend/api/dependencies/conversation_caller.py (new), resource_access.py
- backend/src/rag_backend/api/middleware/auth.py (cookie-only token reader; unused URL-token reader removed)
- backend/src/rag_backend/api/routes/chat_stream.py, conversations.py
- backend/tests/features/anonymous_conversation_ownership.feature (new)
- backend/tests/integration/test_anonymous_conversation_ownership.py (new), conversation_access_support.py (new),
  test_conversation_ownership.py, test_chat_stream.py, test_identity_conversation_safety_net.py
- docs/architecture/openapi.json (regenerated: the stream route docstring)
- backend/tests/snapshots/conversation/conversation_create_anonymous.json (cookie path),
  backend/tests/snapshots/identity/_snapshot.py (a conversation id in a cookie path becomes `<uuid>`)

## Test Evidence

See `.agent/reports/AE-0489.dev-summary.md`: every backend gate except mutation PASS locally with Postgres (test,
diff-cover, openapi-fresh included); 15 table-driven ownership cases; mutation in CI.

## QA Report

External QA, see `.agent/reports/AE-0489.qa.md`: no access hole; review findings fixed with tests.

## Blockers

None (#227 is merged).
