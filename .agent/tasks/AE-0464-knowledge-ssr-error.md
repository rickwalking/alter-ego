# AE-0464 — Knowledge page throws React #419 on every load and has two h1s

Status: In Development
Tier: T1
Priority: Medium
Type: Bug
Area: Frontend
Owner: Worker (Claude) — AE-0453 site scan, SITE-08
Branch: fix/ae-0464-knowledge-ssr-error
Created: 2026-10-22
Updated: 2026-10-22

## Goal

`/dashboard/knowledge` renders without a server-side render error and with one page heading.

## Problem

Found by the AE-0453 site scan (SITE-08). Every load logged `Minified React error #419` (a Suspense boundary
switched to client rendering after a server error), at every viewport and locale. `useDocuments()` is a
`useSuspenseQuery`; during the server render of the client component it called `apiCall("/api/documents")` on the
Node server (relative URL, no session cookie), which fails. The page also rendered "Knowledge Base" as an h1 twice
(shell top bar + the interface's own header).

## Scope

- `useIsClient()` (`lib/use-is-client.ts`, `useSyncExternalStore`): false on the server and during hydration.
- `KnowledgeBaseInterface` renders the list skeleton on the server and only mounts the Suspense list (and its
  query) in the browser; the interface keeps its description but no longer renders its own h1.

## Non-Goals

- No server-side prefetch layer for authenticated APIs.
- Ingestion state / retry (SITE-23, separate ticket).

## Acceptance Criteria

- [x] The server render calls no documents API and shows the skeleton.
- [x] In the browser the documents load as before.
- [x] Exactly one h1 ("Knowledge Base", from the top bar).

## Repro Steps

1. Open `/dashboard/knowledge` with the console open.
2. Before: `Minified React error #419`, two "Knowledge Base" h1. After: no error, one h1.

## Affected Areas

- [ ] Backend
- [x] Frontend
- [x] Tests

## Dependencies

None.

## Progress Log

### 2026-10-22 02:40

Root cause from the source (Suspense query during SSR); failing tests first (2 red), fix.

## Files Touched

- frontend/src/lib/use-is-client.ts (new)
- frontend/src/modules/knowledge/components/knowledge-base-interface.tsx (+ test)
- frontend/src/modules/knowledge/components/knowledge-base-ssr.test.tsx (new)
- frontend/tests/features/knowledge-page-ssr-ae0464.feature (new)

## Test Evidence

See PR. Mutation: CI only (AE-0448).

## QA Report

Pending (CI on the PR head).

## Blockers

None.
