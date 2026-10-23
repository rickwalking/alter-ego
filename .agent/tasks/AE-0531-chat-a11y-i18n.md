# AE-0531 — Chat: screen-reader announcements, labelled focused composer, main landmark, pt/en UI

Status: Review
Tier: T1
Priority: Medium
Type: Bug
Area: Frontend
Owner: Claude — /chat QA (AE-0486 follow-up), CHAT-10, CHAT-11
Branch: fix/ae-0531-chat-a11y-i18n
Created: 2026-10-22
Updated: 2026-10-23

## Goal

Keyboard and screen-reader users can follow and use the chat; the chat UI speaks Portuguese in the PT locale.

## Problem

- CHAT-10: no `aria-live`/`role="log"` (replies and typing were never announced), unlabelled textarea, `outline:
  none` with no replacement, focus dropped to `<body>` after send (the textarea was disabled while streaming), no
  `<main>` on /chat.
- CHAT-11: the chat UI was hard-coded English ("Chat / Alter-Ego assistant", "New chat", placeholder, the "not saved
  after refresh" hint, "Analyzing tone alignment...", aria-labels) although `pt.json` had a `chat` namespace.

## Scope

- Message list: `role="log"` with a label; a polite, atomic live region says "typing", then reads the reply that
  just finished once (never each token; markdown stripped, cut at 280 characters). Loading or switching to another
  conversation announces nothing.
- Composer: `aria-label`, `focus-visible` outline, stays enabled while a reply streams (`busy` only disables Send),
  Send click returns focus to the textarea.
- Public /chat: the conversation area is `<main id="main-content">`, with the shared skip link.
- Header, composer, list, public hint, drawer labels from `chat.*` (en + pt); the typing label is plain language;
  the unused `DASHBOARD_CHAT_TYPING_LABEL` constant is removed.

## Non-Goals

- The notifications bell (removed in the public shell PR) and visual polish.

## Acceptance Criteria

- [x] Labelled log + live region (typing, then the reply once).
- [x] Labelled textarea with a visible focus ring; focus kept after send.
- [x] `<main>` + skip link on /chat.
- [x] Every chat string from translations; en/pt key parity.

## Repro Steps

1. Tab to the composer on /chat → before: no focus ring, no name; after: outlined, "Message to the Alter-Ego".
2. `locale=pt` → before: English chat; after: Portuguese.

## Affected Areas

- [ ] Backend
- [x] Frontend
- [x] Tests

## Dependencies

None. Independent of the markdown PR (AE-0530); whichever merges second is rebased onto the other.

## Progress Log

### 2026-10-22 16:00

Tests first; implemented.

### 2026-10-22 23:40

Ticket id moved to AE-0531 (the earlier ids were taken by other tickets). Gherkin scenario references live in the
tests' JSDoc (comment rule, Pedro 2026-10-22).

### 2026-10-23 00:40

Re-applied on current main (after #248 merged) without the markdown change, so the message row keeps plain text
here; branch fix/ae-0531-chat-a11y-i18n. Chat, public chat and i18n tests pass (52).

### 2026-10-23 02:10

External QA (WARN) findings fixed: two scenarios added to the feature (history load stays silent; long replies are
read as plain text cut at 280 characters) with exact-text tests at the 280/281 boundary and the space before the
ellipsis; Enter / Shift+Enter and "Send stays off while busy with text" tests; a Portuguese-locale render test
(`chat-pt-locale.test.tsx`). Chat and public chat tests: 46 passed.

### 2026-10-23 10:30

PR review fixes: Send puts focus back in the message box only if it had focus when Send was pressed (a tap on a
phone no longer reopens the keyboard); the announcer is a `role="status"` sibling of the log, not inside it, and the
tests query it by role; the notifications button label comes from `chat.notifications` (en/pt); the class-name
focus-ring assertion is gone (the ring is the site-wide one).

## Files Touched

- frontend/src/app/dashboard/chat/chat-header.tsx, chat-composer.tsx, chat-message-list.tsx, chat-message-row.tsx (new, split out), dashboard-chat-view.tsx,
  chat-a11y.test.tsx (new), chat-pt-locale.test.tsx (new)
- frontend/src/app/(public)/chat/public-chat-view.tsx + test, layout.tsx + layout.test.tsx (new)
- frontend/src/modules/editorial-operations/board/chat/constants.ts
- frontend/src/i18n/locales/en.json, pt.json
- frontend/tests/features/chat-a11y-i18n.feature (new)

## Test Evidence

See `.agent/reports/AE-0531.dev-summary.md`: targeted tests pass and `gates.sh --changed-only` is green (0 FAIL) on
44b00d610; the full suites, build and mutation run in CI on the PR.

## QA Report

`.agent/reports/AE-0531.qa.md` (external, round 1 WARN, findings fixed, confirmation round).

## Blockers

None.
