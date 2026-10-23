# AE-0533 — Chat: site header on /chat, mobile fit (dvh, safe area, 16px, 44px), opaque drawer, no fake bell or "PM"

Status: Review
Tier: T1
Priority: Medium
Type: Bug
Area: Frontend
Owner: Claude — /chat QA (AE-0486 follow-up), CHAT-12, CHAT-13, CHAT-14, CHAT-17, CHAT-18
Branch: fix/ae-0533-chat-shell-mobile
Created: 2026-10-22
Updated: 2026-10-23

## Goal

/chat is part of the site (header, home link, language switcher), fits phones, and shows no invented UI.

## Problem

- CHAT-12: no site header/home link/language switcher on /chat; a 64px empty gutter (`pl-16` for a dashboard menu
  button that does not exist there); "New chat" wrapped on 375/390px.
- CHAT-13: 13px textarea (iOS zoom on focus), `h-screen` (100vh) with no `dvh`/safe-area insets, targets < 44px.
- CHAT-14: the mobile conversation drawer was translucent and under the global menu button (z-50).
- CHAT-17: a notifications bell with a hard-coded unread dot that did nothing.
- CHAT-18: every user message carried the owner's initials "PM", visitors included.

## Scope

- Public chat layout: `PublicHeader` + chat in `h-dvh`; `viewport-fit=cover` for this route; composer bottom padding
  `max(16px, env(safe-area-inset-bottom))`.
- `ChatHeader publicShell` drops the gutter and renders as a plain bar (the site header is the only banner
  landmark); "New chat" `whitespace-nowrap`, `min-h-11`; bell removed.
- Side safe-area insets on the page frame (landscape notch).
- Composer: 16px font, 44px Send and min height.
- Drawer: solid `BG_DEEP`, `z-[60]` (backdrop `z-[55]`) above the z-50 menu button.
- User avatar: a neutral person icon.

## Non-Goals

- Visual polish (separate impeccable PR).

## Acceptance Criteria

- [x] Site header on /chat; no gutter; "New chat" on one line.
- [x] dvh + safe area + 16px + 44px targets.
- [x] Opaque drawer above the menu button.
- [x] No bell; no "PM".

## Repro Steps

1. Open /chat at 390×844: before — no header, 64px gutter, wrapped "New chat"; after — site header, no gutter.

## Affected Areas

- [ ] Backend
- [x] Frontend
- [x] Tests

## Dependencies

None. Independent of the other chat PRs (AE-0530..0532); whichever merges later is rebased.

## Progress Log

### 2026-10-22 17:30

Tests first; implemented.

### 2026-10-22 23:55

Ticket id moved to AE-0533 (the earlier ids were taken by other tickets). Gherkin scenario references live in the
tests' JSDoc (comment rule, Pedro 2026-10-22).

### 2026-10-23 01:20

Re-applied on current main (after #248 merged), independent of the a11y/i18n PR: the neutral visitor avatar lives
in `chat-message-list.tsx` here, the header keeps its current strings, and the layout test covers only this ticket's
scenarios. `ChatAvatar` moved to `chat-avatar.tsx` to keep the list under the 200-line lint cap. Chat and public
chat tests pass (41).

### 2026-10-23 03:05

External QA (WARN) findings fixed: the layout no longer exports anything but `default` and `viewport` (the shell
style and viewport values moved to `chat-shell-style.ts`, so Next's layout type check accepts it); tests now cover
the conversations button's 44px size, the drawer's z-index against the menu button's, the public bar's own gutter,
the 44px textarea, the full viewport and frame values, and the assistant marker. The /chat `<main>` landmark and
skip link come from the a11y/i18n PR (AE-0531). Chat and public chat tests: 41 passed.

### 2026-10-23 05:10

Confirmation round follow-ups: the drawer test also requires it to clear the `z-[55]` scrim; new scenario "The
conversation drawer slides away when closed and is a fixed column on wider screens" with its test.

### 2026-10-23 12:20

Rebased onto the a11y PR (AE-0531: the row lives in `chat-message-row.tsx`, which now uses `chat-avatar.tsx`; the
skip link and the single `<main>` come from there). PR review fixes: z-index could not lift the drawer above the menu
button (the dashboard content sits in its own `position: relative; z-index: 1` context), so while the drawer is open
the menu button is now hidden and `inert` (`use-menu-button-hidden.ts`, marked by `data-dashboard-menu-button` in
the dashboard layout), with tests on the real outcome; drawer/scrim z-index back to their original values. `h-dvh`
has an `h-screen` fallback; the frame pads the top safe-area inset; the composer no longer mixes `padding` with
`paddingBottom`.

### 2026-10-23 18:20

Review should-fix: the menu button is hidden only while the drawer is open on a narrow screen (the sidebar's
`(max-width: 767px)` query, now one shared constant); rotating a phone to 768px+ gives it back. Tests for both.

## Files Touched

- frontend/src/app/(public)/chat/layout.tsx, chat-shell-style.ts (new) + test, public-chat-view.tsx
- frontend/src/app/dashboard/chat/chat-header.tsx, chat-composer.tsx, chat-sidebar.tsx, chat-message-list.tsx, chat-avatar.tsx (new), use-menu-button-hidden.ts (new) + test, app/dashboard/layout.tsx +
  layout-menu-button.test.tsx (new), constants/a11y.ts,
  dashboard-chat-view.tsx, chat-shell.test.tsx (new)
- frontend/tests/features/chat-shell-mobile.feature (new)

## Test Evidence

See `.agent/reports/AE-0533.dev-summary.md`: targeted tests pass and `gates.sh --changed-only` is green (0 FAIL) on
7a8497b68; the full suites, build and mutation run in CI on the PR.

## QA Report

`.agent/reports/AE-0533.qa.md` (external, round 1 WARN, findings fixed, confirmation round).

## Blockers

None.
