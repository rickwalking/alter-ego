# AE-0487 — Chat: replies render exactly as streamed, one send per press, pending and failed turns, auto-scroll

Status: In Development
Tier: T1
Priority: High
Type: Bug
Area: Frontend
Owner: Claude — /chat QA (AE-0486 follow-up), CHAT-02, CHAT-05, CHAT-06, CHAT-09
Branch: fix/ae-0486-chat-stream-state
Created: 2026-10-22
Updated: 2026-10-22

## Goal

Every streamed reply shows each token once, in order, in one bubble; a double press sends one message; the message
shows as pending while the conversation is created and survives a failure; the list follows new text unless the
reader scrolled up.

## Problem

Found by the /chat QA:

- CHAT-02: every streamed reply was garbled ("Hey! I! I'm Pedro", lost opening fence, reply split over two bubbles).
  `appendToken` read `contentRef` and wrote `msgIdRef` inside the state updater; when several tokens were batched the
  first updater created the message with the whole accumulated text and the next ones appended their tokens again;
  a COMPLETE in the same batch reset the refs before the updaters ran, which dropped the first token and opened a
  second bubble.
- CHAT-05: a double Enter created 3 conversations and 3 billed streams (no in-flight guard while the conversation was
  being created).
- CHAT-06: nothing showed during the create round-trip, and on failure the typed text was wiped and no bubble kept.
- CHAT-09: the list never scrolled; new replies landed below the fold.
- The stream ended with two `complete` events (the agent's own plus the service's).

## Scope

- Token fold is a pure updater over a stream id fixed when the token arrives.
- `useSseChat().sendMessage(content, target)` takes the conversation id or a creator, shows the user bubble and the
  typing state at once, ignores a second send while a turn is in flight, and returns `sent` / `failed` / `ignored`.
  On `failed` the views give the text back; the next send replaces the unanswered bubble.
- `useSseChat().isBusy()` answers synchronously; the composer checks it before clearing, so a send that would be
  ignored keeps the typed text (added during review).
- `useStickToBottom` keeps the list pinned to the bottom unless the reader scrolled up (their own send re-pins it).
- Backend: the agent's `complete` is not forwarded; the service's one (after saving) is the only one.

## Non-Goals

- Localized error copy and Retry (separate /chat PR).
- Incremental server streaming (the server still sends the reply at the end; tracked separately).

## Acceptance Criteria

- [x] Batched tokens render once, in order, in one bubble (tests reproduce the QA's "Tudo ótimo! ótimo!" case).
- [x] Double send: one conversation, one stream.
- [x] Pending bubble + typing indicator during conversation creation; composer disabled.
- [x] Failure keeps the bubble and gives the text back; resend replaces the failed bubble.
- [x] Auto-scroll that respects a reader who scrolled up.
- [x] One `complete` event per stream.

## Repro Steps

1. Open /chat, send "Tudo bem?".
2. Before: duplicated words / split bubble; double Enter → 3 conversations. After: clean reply, one conversation.

## Affected Areas

- [x] Backend
- [x] Frontend
- [x] Tests

## Dependencies

None.

## Progress Log

### 2026-10-22 11:00

Failing tests first: the token-fold tests failed on main with exactly the QA's symptoms
(`'Tudo ótimo! ótimo! Eu'`, `'python'` instead of `'```python'`, `['', 'second']`). Fixed the fold, the send path,
the views, the list scroll and the duplicate `complete`.

## Files Touched

- frontend/src/lib/sse-chat-stream.ts, use-chat-stream.ts, use-stick-to-bottom.ts (new) + tests
- frontend/src/modules/conversation/constants.ts (new), index.ts, hooks/types.ts, hooks/use-sse-chat.ts + test
- frontend/src/app/(public)/chat/public-chat-view.tsx + test, app/dashboard/chat/dashboard-chat-view.tsx,
  chat-message-list.tsx + test (new), use-chat-send.ts (new, shared by both views), types.ts (new)
- frontend/tests/features/chat-stream-state.feature (new)
- backend/src/rag_backend/application/services/chat_stream_service.py,
  backend/tests/unit/application/test_chat_stream_single_complete.py (new),
  backend/tests/features/alter_ego_chat_sse.feature

## Test Evidence

Pending (local gates, mutation in CI).

## QA Report

Pending.

## Blockers

None.
