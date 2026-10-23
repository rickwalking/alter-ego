# AE-0530 — Chat: assistant replies render markdown safely

Status: In Development
Tier: T1
Priority: Medium
Type: Bug
Area: Frontend
Owner: Claude — /chat QA (AE-0486 follow-up), CHAT-08
Branch: fix/ae-0530-chat-markdown
Created: 2026-10-22
Updated: 2026-10-23

## Goal

Assistant replies show headings, bold, lists, code blocks and clickable links instead of raw `**`, `##`, fences
and `[text](url)`, without opening the chat to unsafe content.

## Problem

CHAT-08: replies rendered as `pre-wrap` text; links were not clickable.

## Scope

- `ChatMarkdown` (react-markdown, already a dependency): `skipHtml`, an allow-list without images, links only for
  http(s)/mailto/same-site (`isSafeMarkdownHref`) with `target=_blank` and `rel="noopener noreferrer nofollow"`.
- Only assistant messages render markdown; the visitor's own text stays as typed.
- Protocol-relative links (`//host`) are no longer treated as same-site (shared `isSafeMarkdownHref`).
- Blog posts share `isSafeMarkdownHref`, so a protocol-relative link in a post also renders as text now.
- A link whose only content was an (dropped) image shows its URL; message rows shrink to the screen
  (`min(720px, 100%)`, `min-width: 0`) so code blocks scroll inside themselves on phones.

## Non-Goals

- GFM tables/strikethrough (no remark-gfm dependency added).

## Acceptance Criteria

- [x] Formatting rendered without raw markers; code blocks in `<pre>`.
- [x] Safe, clickable links; `javascript:` links stay text.
- [x] No raw HTML or images from a reply.
- [x] User messages unchanged.

## Repro Steps

1. Ask the chat for "a python code block and a link to python.org".
2. Before: literal fences and `[..](..)`; after: a code block and a clickable link.

## Affected Areas

- [ ] Backend
- [x] Frontend
- [x] Tests

## Dependencies

AE-0510 (#248, merged).

## Progress Log

### 2026-10-22 15:30

Tests first (markdown, links, HTML/image stripping, user text); implemented.

### 2026-10-22 23:30

Ticket id moved to AE-0530 (the earlier ids were taken by other tickets). Gherkin scenario references live in the
tests' JSDoc (comment rule, Pedro 2026-10-22).

### 2026-10-23 00:20

Re-applied on current main after #248 merged; branch fix/ae-0530-chat-markdown. The protocol-relative link test fails
on main's `isSafeMarkdownHref` and passes with the fix; chat and blog public-post tests pass.

### 2026-10-23 02:30

External QA (WARN) findings fixed: an unsafe link whose only content was an image now shows its target as text
(the test failed before the fix); new scenario "Unsafe or empty links stay readable text" with tests for upper-case
and padded `javascript:` and empty targets; tests for same-site and mailto links, a mixed image+text label, every
heading level, and the visitor's line breaks. Markdown tests: 16 passed.

## Files Touched

- frontend/src/app/dashboard/chat/chat-markdown.tsx (new) + test, chat-message-list.tsx
- frontend/src/lib/safe-markdown-href.ts + test
- frontend/tests/features/chat-markdown.feature (new)

## Test Evidence

Pending.

## QA Report

Pending.

## Blockers

None.
