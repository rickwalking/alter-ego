# AE-0471 — Public /blog empty state shows owner instructions to visitors

Status: In Development
Tier: T1
Priority: Low
Type: Bug
Area: Frontend
Owner: Worker (Claude) — AE-0453 site scan, SITE-17
Branch: fix/ae-0471-blog-empty-state
Created: 2026-10-22
Updated: 2026-10-22

## Goal

With no published article, visitors read a message meant for them and get somewhere to go.

## Problem

Found by the AE-0453 site scan (SITE-17). With 0 published posts the public `/blog` (and the homepage latest-posts
empty state, same message) told visitors "No blog posts yet. Generate one with AI, or create one from a carousel."
— an owner instruction a visitor cannot follow.

## Scope

- `blog.noPosts` rewritten for visitors (en/pt); new `blog.browseCarousels`.
- `/blog` empty state (`BlogEmptyState`) adds a link to `/carousels`.

## Non-Goals

- Publishing any blog post (data).

## Acceptance Criteria

- [x] `/blog` with no posts: visitor message + link to the carousels; no generation/creation instruction.
- [x] en and pt copies free of owner instructions.

## Repro Steps

1. Open `/blog` while no post is published.
2. Before: "Generate one with AI…". After: "No articles are published yet. In the meantime, browse the visual
   carousels." + "Browse the carousels".

## Affected Areas

- [ ] Backend
- [x] Frontend
- [x] Tests

## Dependencies

None.

## Progress Log

### 2026-10-22 06:00

Failing tests first; fix; CI freeze (rule 11): committed locally, pushed once the queue drains.

## Files Touched

- frontend/src/app/(public)/blog/blog-empty-state.tsx (+ test, new)
- frontend/src/app/(public)/blog/page.tsx
- frontend/src/i18n/locales/en.json, pt.json
- frontend/tests/features/blog-empty-state-ae0471.feature (new)

## Test Evidence

Local frontend gates (lint, typecheck, gherkin-refs, format, integrity, dead-code, blog-v1-dead-code, duplication,
dead-files, legacy-guard, legacy-inventory, component-types, schema-drift, test 2039): PASS. Mutation: CI only.

## QA Report

Pending (CI on the PR head).

## Blockers

CI freeze (rule 11) — push pending.
