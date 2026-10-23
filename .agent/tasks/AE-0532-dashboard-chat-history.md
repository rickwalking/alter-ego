# AE-0532 — Dashboard chat: reply survives a refresh, real titles, working search, signed-in /chat goes to history

Status: In Development
Tier: T1
Priority: Medium
Type: Bug
Area: Full-stack
Owner: Claude — /chat QA (AE-0486 follow-up), CHAT-15, CHAT-16, CHAT-19
Branch: fix/ae-0532-dashboard-chat
Created: 2026-10-22
Updated: 2026-10-23

## Goal

The dashboard chat behaves like a real history: a reply streaming during a refresh shows up on its own, conversations
carry real titles and can be searched, and a signed-in user opening /chat lands on it.

## Problem

- CHAT-15: after a refresh mid-stream only the user message showed, with no "replying" state; the reply (saved by
  the server) appeared only after a second manual reload.
- CHAT-16: every conversation was titled and previewed "New conversation"; the search box did nothing; avatars cycled
  fake "AE/KB/WF" by list index; an always-false unread dot.
- CHAT-19: a signed-in user on /chat got the visitor view ("Sign in to keep chat history") and no history.

## Scope

- History polling (`reply-wait.ts`): while the history ends with a user message less than 3 minutes old and nothing
  streams, it is re-read every 2 s (at most 90 times; clock skew cannot extend it) and the typing indicator shows
  (`useAwaitingReply`, re-checked on a clock so it ends when the window passes even if no reply arrives).
- Backend: the stream titles an untitled conversation from its first message (first line, ≤ 60 chars, ellipsis);
  `Conversation.ensure_title_from`. The sidebar list is re-read after each reply so the title appears.
- Sidebar: title + time only (no avatars, preview or fake unread), accent/case-insensitive search with a "no matches"
  note; pt/en labels.
- /chat: a valid, unexpired session redirects to /dashboard/chat (`isLiveSession`); visitors and expired sessions keep
  the public chat.

## Non-Goals

- Resuming the SSE stream itself after a refresh (polling the saved reply is enough).
- Search in message bodies.

## Acceptance Criteria

- [x] Refresh mid-stream: typing indicator, then the reply without another reload.
- [x] Titles from the first message; existing titles kept.
- [x] Search filters; no fake avatars/unread.
- [x] Signed-in /chat → /dashboard/chat.

## Repro Steps

1. Dashboard chat → new chat → send → reload after 3 s. Before: no reply until a second reload. After: it appears.
2. Before: every item "New conversation" with AE/KB/WF. After: the first message as title.

## Affected Areas

- [x] Backend
- [x] Frontend
- [x] Tests

## Dependencies

None. Independent of the markdown (AE-0530) and a11y/i18n (AE-0531) PRs; whichever merges later is rebased.

## Progress Log

### 2026-10-22 17:00

Tests first; implemented. `useSseChat`'s New-chat reset moved into `useStartNewChat` (function-size rule).

### 2026-10-22 23:50

Ticket id moved to AE-0532 (the earlier ids were taken by other tickets). Gherkin scenario references live in the
tests' docstrings and JSDoc (comment rule, Pedro 2026-10-22).

### 2026-10-23 01:00

Re-applied on current main (after #248 merged): `useSseChat` returns both the retry state and `awaitingReply`;
the dashboard view takes `useTranslations` itself. The `// Scenario:` lines in the touched tests became JSDoc.
Targeted vitest (164) and pytest (chat stream + titles, 78) pass; backend mypy clean.

### 2026-10-23 02:50

External QA (WARN) findings fixed: the reply's double re-read (history + sidebar list) is asserted exactly (scenario
"The sidebar shows a new conversation's title after its first reply"); the history polling wiring is tested with fake
timers (`use-conversation-messages-poll.test.ts`); the /chat redirect moved into `redirect-signed-in.ts` and is tested
for a live session, no cookie and an expired session (the React compiler keeps the page itself from being called
outside render); a blank search has its own scenario; backend tests cover a whitespace-only title and the space before
the ellipsis. Frontend 96 and backend title 10 tests pass.

## Files Touched

- backend/src/rag_backend/domain/models/conversation.py, domain/constants/conversation.py,
  application/services/chat_stream_service.py; backend/tests/unit/domain/test_conversation_title.py (new),
  backend/tests/features/conversation_titles.feature (new)
- frontend/src/modules/conversation/reply-wait.ts (new) + test, hooks/use-awaiting-reply.ts (new) + test,
  constants.ts, hooks/use-chat.ts, hooks/types.ts,
  hooks/use-sse-chat.ts + tests
- frontend/src/modules/identity/lib/live-session.ts (new) + test, index.ts; app/(public)/chat/page.tsx, redirect-signed-in.ts (new) + test,
  hooks/use-conversation-messages-poll.test.ts (new)
- frontend/src/app/dashboard/chat/chat-sidebar.tsx + chat-sidebar-search.test.tsx (new), dashboard-chat-view.tsx
- frontend/src/modules/editorial-operations/board/chat/adapters/chat-adapter.ts + test, types.ts
- frontend/src/i18n/locales/en.json, pt.json; frontend/tests/features/dashboard-chat.feature (new)

## Test Evidence

Pending.

## QA Report

Pending.

## Blockers

None.
