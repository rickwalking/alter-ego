# AE-0474 — "New Post" creates an empty draft on click

Status: In Development
Tier: T1
Priority: Low
Type: Bug
Area: Frontend
Owner: Worker (Claude) — AE-0453 site scan, SITE-21
Branch: fix/ae-0474-new-post-form-first
Created: 2026-10-22
Updated: 2026-10-22

## Goal

"New Post" opens a create form; the draft is created only when the form is submitted.

## Problem

Found by the AE-0453 site scan (SITE-21; blocked by the QA mutation guard on prod): clicking "Novo Post" sent
`POST /api/blog-posts` immediately with the title "Untitled draft", so every exploratory click left an empty draft.
Owner decision (2026-10-22): open a create form first and only POST on submit.

## Scope

- `NewBlogPostAction`: the "New Post" button opens a `NeonModal` ("Create New Blog Post") with a required Title
  (max 255, the API limit); Create (disabled for a blank title) creates the draft and opens its editor; Cancel/Escape
  close without creating; a failed create keeps the form open with the localized error.
- `useNewBlogPost` is the form state (show/hide/title/submit); the page no longer shows the create error as a list
  notice.

## Non-Goals

- "Generate with AI" (already a form).

## Acceptance Criteria

- [x] Click opens the form, nothing is created.
- [x] Submit creates one draft with the trimmed title and opens the editor.
- [x] Blank title: Create disabled; Cancel creates nothing; failure shows the error in the form.

## Repro Steps

1. `/dashboard/blog-posts` → "New Post".
2. Before: an "Untitled draft" is created at once. After: a title form opens.

## Affected Areas

- [ ] Backend
- [x] Frontend
- [x] Tests

## Dependencies

None.

## Progress Log

### 2026-10-22 07:20

Failing tests first; fix; CI freeze (rule 11): committed locally.

## Files Touched

- frontend/src/app/dashboard/blog-posts/new-blog-post-modal.tsx (+ test, new)
- frontend/src/app/dashboard/blog-posts/use-new-blog-post.ts (+ test)
- frontend/src/app/dashboard/blog-posts/page.tsx, types.ts
- frontend/tests/features/new-post-form-first-ae0474.feature (new)

## Test Evidence

Local frontend gates (lint, typecheck, gherkin-refs, format, integrity, dead-code, blog-v1-dead-code, duplication,
dead-files, legacy-guard, legacy-inventory, component-types, schema-drift, test 2045): PASS. Mutation: CI only.

## QA Report

Pending (CI on the PR head).

## Blockers

CI freeze (rule 11) — push pending.
