# AE-0137 — Disambiguate useBlogPosts + publishing module behind a public contract

Status: Ready
Tier: T2
Priority: High
Type: Task
Area: Frontend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0137-publishing-module-blog-hooks
Kanban Card: TBD
Created: 2026-06-16
Updated: 2026-06-16

## Goal

Migrate features/blog + features/publish into modules/publishing (blog/distribution/scheduling) behind a public contract, and disambiguate the two useBlogPosts() hooks: use-carousel-blog (carousel-origin blog posts = BlogPost origin=carousel) vs use-blog-posts (first-class BlogPost), aligning names to the backend BlogPost.origin split. NOTE: the glossary REJECTS the name CarouselArticle; the canonical term is BlogPost (origin = carousel). Phase 7 keeps BOTH hooks (behavior-preserving); collapsing to a single representation is deferred (Phase 8).

## Problem

Today `frontend/src/features/**` is feature-organized with 23 grandfathered cross-feature imports and no module public-contract boundary; feature names diverge from the backend bounded-context glossary, persona/personas are duplicated, and two `useBlogPosts()` hooks conflate carousel articles with first-class blog posts. The frontend needs the same bounded-context ownership + enforceable boundaries the backend now has.

## Scope

Behavior-preserving (App Router URLs + UI unchanged; green gates held; boundary ratchet down-only). Frontend-only. Work is scoped to this ticket's slice of the feature->module migration per `docs/plans/phase-7-frontend-alignment.md`; re-export shims keep `@/` paths resolving during the move.

## Non-Goals

- No backend changes (frontend-only).
- No App Router URL changes.
- No UI/behavior change; no test deletion or gate weakening.
- No exhaustive component re-homing or legacy-shim removal (deferred to Phase 8).

## Modularization Alignment (2026-06-16)

Phase 7 of the modularization plan (§Phase 7 "Align the frontend"). **Behavior-preserving** frontend
reorganization: App Router URLs unchanged, the green gates (typecheck + eslint + lint:boundaries + 822 Vitest
tests + check:legacy) stay green per ticket, and the feature/module-boundary ratchet only goes DOWN. Features
migrate into `frontend/src/modules/<context>` sharing the backend glossary (knowledge/identity/conversation/
editorial/carousel-presentation/publishing + editorial-operations/persona/quality), each behind a public contract;
re-export shims keep `@/` paths resolving during migration (object-identity, mirroring backend AE-0126).
ZERO gate-gaming (no new eslint-disable/@ts-ignore/@ts-expect-error/skipped tests/lowered thresholds/baseline
additions). Soft precondition: Phase 6 (PR #20) merging only finalizes glossary naming; this frontend-only work reads the committed glossary doc and does not hard-block on the backend merge. See `docs/plans/phase-7-frontend-alignment.md`.

## Acceptance Criteria

- [ ] modules/publishing SHALL own blog + distribution + scheduling behind a public contract; cross-context imports go through it
- [ ] The carousel-derived hook (use-carousel-blog.ts `useBlogPosts`, currently the one re-exported via features/blog/hooks/index.ts) SHALL be renamed to `useCarouselBlogPosts` (BlogPost origin=carousel — the glossary-rejected name CarouselArticle is NOT used); the first-class hook (use-blog-posts.ts `useBlogPosts`, imported directly by app/dashboard/blog-posts/*) keeps `useBlogPosts`. Every consumer's resolved hook SHALL be unchanged; re-export shims keep old paths resolving
- [ ] App Router /blog + dashboard blog routes SHALL render byte-identically (URLs + UI unchanged)
- [ ] The boundary ratchet SHALL ratchet DOWN or hold; typecheck/eslint/test/build green

## Gherkin Scenarios

Not applicable — behavior-preserving reorganization; verified by the green-gate safety net (typecheck + eslint
+ lint:boundaries + Vitest 822 + check:legacy) and the App Router URL inventory.

## Dependencies

- Blocks: AE-0138, AE-0140, AE-0142
- Blocked by: AE-0136
- Related: AE-0134

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-16

Ticket created by planner (Phase 7 breakdown).

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Decision Log

Pending.

## Blockers

None.

## Final Summary

Pending.
