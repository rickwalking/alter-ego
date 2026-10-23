# AE-0530 — Chat: assistant replies render markdown safely

Status: Review
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

### 2026-10-23 05:20

Confirmation round follow-up: test for a safe link whose label is only spaces (it shows the target).

### 2026-10-23 11:40

Re-applied on top of the a11y PR (the renderer now sits in `chat-message-row.tsx`). PR review fixes: a crafted
deeply nested reply (`- `x900, `>`x3000) crashed the page with a stack overflow; replies over 20 nesting levels or
20000 characters now render as plain text, and an error boundary falls back to plain text if rendering still throws.
`ChatMarkdown` is memoized on the text. Hrefs are read as a browser reads them (tabs/newlines dropped, controls
trimmed) before the safety check. Only external http(s)/mailto links open a new tab; web links show their host.
Regression tests for data:/vbscript: (mixed case), entity-encoded javascript:, autolinks, reference-style links, the
tab-split `//` link, and the nesting cases.

## Files Touched

- frontend/src/app/dashboard/chat/chat-markdown.tsx (new) + tests, chat-markdown-guard.ts, chat-markdown-boundary.tsx,
  chat-markdown-link.tsx (new), chat-markdown-safety.test.tsx, chat-markdown-memo.test.tsx (new), chat-message-row.tsx
- frontend/src/lib/safe-markdown-href.ts + test
- frontend/tests/features/chat-markdown.feature (new)

## Test Evidence

See `.agent/reports/AE-0530.dev-summary.md`: targeted tests pass and `gates.sh --changed-only` is green (0 FAIL) on
591449245; the full suites, build and mutation run in CI on the PR.

## QA Report

`.agent/reports/AE-0530.qa.md` (external, round 1 WARN, findings fixed, confirmation round).

## Blockers

None.
