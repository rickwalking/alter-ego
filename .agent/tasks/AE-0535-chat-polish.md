# AE-0535 — Chat polish: intro and suggested questions, auto-growing composer, Stop control

Status: Review
Tier: T1
Priority: Low
Type: Improvement
Area: Full-stack
Owner: Claude — /chat QA (AE-0486 follow-up), CHAT-21, CHAT-22
Branch: fix/ae-0535-chat-polish
Created: 2026-10-22
Updated: 2026-10-23

## Goal

A new chat introduces the Alter-Ego and offers questions to start with; the composer grows with the text; a
streaming reply can be stopped.

## Problem

- CHAT-21: the composer stayed one line (42px) for multi-line input.
- CHAT-22: the first screen was a blank panel with no intro or suggested prompts; the typing label read "Analyzing
  tone alignment..." (fixed earlier as plain language); no way to stop a reply.

## Scope

- `ChatEmptyState`: who the Alter-Ego is plus four suggested questions (en/pt); a pick is sent at once (`sendNow`).
  Shown on an empty public chat and on a new dashboard chat (never while an existing conversation loads).
- Composer auto-grows to 160px, then scrolls (height kept in React state, so hydration stays clean).
- While a reply streams, Send becomes "Stop the reply" (`useSseChat().stopStreaming`); the text that arrived stays.
  Stop aborts the request; the server keeps writing and saves the full reply in its own task (the dashboard
  history PR, AE-0532), so the question never dangles. With history on, Stop re-reads the history and the list;
  when the reply saved for this question starts with the stopped text, only the saved reply shows. While a reply
  is only awaited after a refresh (nothing streaming here), Send is off and Stop is not offered.
- The composer re-measures on window resize.
- Send/Stop buttons get hover, active, disabled and focus-visible states; motion respects reduced motion.
- On wide screens the thread, the "not saved" note and the message box line up in one centred column (48rem), like
  the intro, instead of the visitor's bubble sitting at the far right edge.
- The screen-reader announcement reads a link's or image's text, never its address.

## Non-Goals

- Copy/regenerate actions.

## Acceptance Criteria

- [x] Intro + suggestions in en/pt; picking one sends it.
- [x] Composer grows up to 160px.
- [x] Stop control while streaming; partial text kept.
- [x] Plain-language typing label.

## Repro Steps

1. Open /chat. Before: blank panel. After: intro and four questions.
2. Type four lines. Before: stays 42px. After: grows to fit.

## Affected Areas

- [x] Backend
- [x] Frontend
- [x] Tests

## Dependencies

AE-0530, AE-0531, AE-0532, AE-0533 (the other chat PRs): this branch is opened after they merge and is based on
main with all of them.

## Progress Log

### 2026-10-22 18:00

Polish pass (impeccable, polish mode) on the chat; checked in the browser at 1440×900 and 390×844, en and pt.

### 2026-10-23 00:00

Ticket id moved to AE-0535 (the earlier ids were taken by other tickets). Gherkin scenario references live in the
tests' JSDoc (comment rule, Pedro 2026-10-22).

### 2026-10-23 04:40

Second polish pass (impeccable, polish mode) in the browser at 1440x900 and 390x844, en and pt, with the API mocked:
centred reading column for the thread, note and message box; links read by their text in the announcement. Checked:
16px message box, 44px targets, no horizontal overflow at 390px, Stop replaces Send while a reply is written. The
focus ring follows the site-wide `--color-ring`. Before (prod) and after screenshots: `docs/pr-assets/ae-0535/`.
Server side, the reply is generated and saved in full before the stream sends anything, so Stop never leaves the
question unanswered.

### 2026-10-23 06:10

External QA (WARN) findings fixed. Server: Starlette (ASGI 2.3 under uvicorn) cancels the stream when the client
disconnects, and `except Exception` missed `CancelledError`, so a Stop left the question unanswered; now the turn is
saved shielded and the cancel re-raised (`chat_stopped_reply.feature`, tests incl. an anyio task-group cancel that
fails without the shield). Client: the stopped-part drop only looks at replies saved after this question
(`merge-messages.ts`, which also keeps `use-sse-chat.ts` under 400 lines); Stop re-reads history and the list; tests
for stop-then-send, suggestion while busy, the 160px boundary and shrink, resize, Portuguese empty state, the note
column; the suggestion hover uses the cyan token.

### 2026-10-23 06:50

Confirmation round: backend stop handling confirmed correct; one new issue fixed: with history on, a new turn now
starts from the history, so a stopped part no longer reappears next to the saved reply after the next send (the
regression test fails without the fix); the stopped-part drop only applies once streaming has ended, so a reply in
progress is never hidden behind an earlier answer to the same question. Accepted: after a stop, the live region
reads the text that had arrived; the reply the server saves later is not announced (the user chose to stop).

### 2026-10-23 07:20

Second confirmation follow-up: a failed reply with history on now re-reads the history too (the server saved the
question and the apology), so the next send never wipes the only copy of that turn; the refresh/stop hooks moved
to `use-stop-streaming.ts` (keeps `use-sse-chat.ts` under 400 lines).

### 2026-10-23 16:30

Rebuilt on main with the merged a11y PR and the markdown, dashboard-history and shell PRs: the backend stop handling
of this branch is dropped (the dashboard-history PR saves every reply in a detached task, so a Stop cannot leave the
question unanswered); Send and Stop put focus back in the message box only if it had focus (the a11y PR's rule);
the announcer stays a `role="status"` sibling of the log; the composer stays locked while a reply is awaited.

### 2026-10-23 19:30

Final external review fixed: only history rows saved since the turn's question was sent (60 s clock-skew
allowance) can de-duplicate its bubbles or stand in for its reply, so the same question asked again is never
hidden or bound to its older answer; anchoring on the question's time (not a history index) stays right across a
conversation switch and a send made before the history loaded (`merge-messages.ts`, tests); the dashboard test
now also checks Stop is not offered while a reply is only awaited. Before/after screenshots re-taken on this build: `docs/pr-assets/ae-0535/`.

### 2026-10-23 21:00

PR review round (Pedro wants it merged):
1. After a Stop (history on) the turn still counts as being answered (typing shown, Send off) until the reply the
   server saves for that question is in the history; without history, the next send keeps the stopped turn on
   screen. A 409, or the server's in-flight error event (now carrying `code: "turn_in_flight"`), shows
   "Still finishing the previous reply" (en/pt) with Try again.
2. Stop is offered only once the answer stream has opened, so a stop can no longer lose a message that is still
   being sent (or leave an empty conversation behind).
3. The auto-growing composer adds the border (offsetHeight - clientHeight) to the measured height.
Also: the announcer drops bare and autolinked web addresses and reads titled links by their text.

## Files Touched

- frontend/src/app/dashboard/chat/chat-empty-state.tsx (new), chat-composer-actions.tsx (new), chat-composer.tsx,
  chat-message-list.tsx, use-chat-send.ts, types.ts, dashboard-chat-view.tsx, chat-polish.test.tsx (new),
  chat-shell.test.tsx, chat-a11y.test.tsx; app/(public)/chat/public-chat-view.tsx
- docs/pr-assets/ae-0535/ (before/after screenshots)
- frontend: hooks/use-sse-chat-stop.test.ts (new), chat-errors.ts + test, constants.ts, en/pt chat.errors.busy
- backend: chat_stream_service.py (error-event code), domain/constants/chat_stream.py, test_chat_stream_disconnect.py
- frontend/src/modules/conversation/hooks/use-sse-chat.ts, merge-messages.ts (new) + test, use-stop-streaming.ts (new), types.ts,
  use-sse-chat-turns.test.ts; queries.ts; app/dashboard/chat/use-chat-send-suggestion.test.ts (new),
  chat-pt-locale.test.tsx; app/(public)/chat/public-chat-view.test.tsx
- frontend/src/i18n/locales/en.json, pt.json; frontend/tests/features/chat-polish.feature (new),
  chat-a11y-i18n.feature

## Test Evidence

See `.agent/reports/AE-0535.dev-summary.md`: targeted tests pass and `gates.sh --changed-only` is green (0 FAIL) on
8abf4f890; the full suites, build and mutation run in CI on the PR.

## QA Report

`.agent/reports/AE-0535.qa.md` (external, round 1 WARN, findings fixed, confirmation round).

## Blockers

Opened only after AE-0530..0533 are merged into main.
