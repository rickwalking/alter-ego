# AE-0510 — Chat UI: localized error messages with Retry, expired-session sign-in, 2000-character limit

Status: In Development
Tier: T1
Priority: Medium
Type: Bug
Area: Frontend
Owner: Claude — /chat QA (AE-0486 follow-up), CHAT-03 (frontend), CHAT-07
Branch: fix/ae-0486-chat-errors-ui
Created: 2026-10-22
Updated: 2026-10-22

## Goal

A failed chat turn is explained in the visitor's language with the action that helps (Try again, or Sign in), and
the composer enforces the API's 2000-character limit.

## Problem

Found by the /chat QA:

- CHAT-03: the chat rendered raw errors: `Failed to fetch`, `HTTP 422`, the LangGraph recursion text; no retry.
- CHAT-07: no client-side limit; a 2,500-character message was discarded with "HTTP 422". The zod `chatRequestSchema`
  allowed 10000 while the API allows 2000.
- Since AE-0486 a signed-in user whose token expired mid-chat gets 404 on their own conversation (shown as
  "HTTP 404"); show "session expired, sign in again".

## Scope

- `classifyChatError` maps failures to kinds (offline, tooLong, limit, notFound, sessionExpired, generic);
  `SseHttpError` carries the status; the hook exposes the kind, never a message.
- `ChatErrorBanner`: localized text (en/pt), Try again (not for tooLong / notFound / sessionExpired), Sign in link
  back to the chat on a 401.
- Dashboard: a 404 on the user's own conversation re-reads the conversation list; an expired session gets a 401 there
  and the API client sends the user to the login page (session expired) and back; a valid session sees "no longer
  available". The chat route's crash view no longer prints the raw error message.
- Offline is a network-failure `TypeError` ("Failed to fetch", "NetworkError…", "Load failed") or `navigator.onLine`
  false; other errors are generic.
- `useChatSend().retry` re-sends the last failed message.
- A conversation that is gone (a visitor's conversation past Pedro's hard 60-minute limit, or a deleted one)
  shows "This conversation is no longer available. Start a new chat." with a Start a new chat button.
- Composer `maxLength=2000` and an "n of 2000 characters" counter from 1600 characters (`aria-describedby`);
  `chatRequestSchema` max is 2000 (`CHAT_MESSAGE_MAX_LENGTH`).

## Non-Goals

- Localizing the rest of the chat UI (separate a11y + i18n PR).

## Acceptance Criteria

- [x] No status code or exception text in the UI; every kind has en + pt copy.
- [x] Retry re-sends the failed message.
- [x] Expired session on the dashboard → "Your session expired" + Sign in link.
- [x] Composer stops at 2000 characters with a counter near the limit.

## Repro Steps

1. Go offline on /chat and send → before: "Failed to fetch"; after: "You seem to be offline…" + Try again.
2. Paste 2,500 characters → before: "HTTP 422" and text lost; after: the composer stops at 2000 and shows the counter.

## Affected Areas

- [ ] Backend
- [x] Frontend
- [x] Tests

## Dependencies

AE-0487 (#230, merged): the send result and the shared `useChatSend`.

## Progress Log

### 2026-10-22 15:00

Tests first for the classification, banner, composer and retry; implemented.

## Files Touched

- frontend/src/lib/sse-http-error.ts (new), sse-client.ts
- frontend/src/constants/chat.ts (new), schemas/chat.ts
- frontend/src/modules/conversation/chat-errors.ts (new) + test, constants.ts, index.ts, hooks/types.ts,
  hooks/use-sse-chat.ts + test
- frontend/src/app/dashboard/chat/chat-error-banner.tsx (new) + test, chat-composer.tsx + test (new),
  use-recheck-session.ts (new) + test, error.tsx,
  use-chat-send.ts, types.ts, dashboard-chat-view.tsx; app/(public)/chat/public-chat-view.tsx + test
- frontend/src/i18n/locales/en.json, pt.json
- frontend/tests/features/chat-errors-ui.feature (new)

### 2026-10-22 23:00

Rebased on main after #230; the ticket id moved from AE-0490 (taken by another ticket) to AE-0510. Gherkin scenario
references live in the tests' JSDoc (comment rule, Pedro 2026-10-22).

## Test Evidence

Pending.

## QA Report

Pending.

## Blockers

None.
