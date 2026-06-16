# ADR-010: Suspense-based data loading (Server Components + TanStack Query + React 19 `use()`)

## Status

Accepted

## Context

The frontend (Next.js 16 App Router, React 19) must not fetch data with `useEffect`. That anti-pattern causes
request waterfalls, duplicated loading/error state, race conditions, and untestable effects. The codebase
already forbids it (`frontend/CLAUDE.md` "NEVER use useEffect for Data Fetching"; the
`minimizing-useeffect-guide.md` guide; an ESLint `no-restricted-syntax` rule blocking `fetch()` inside
`useEffect`), but the *positive* decision — which data-loading mechanisms ARE canonical, and when to use each —
was not recorded as an architecturally significant decision. PR #21 (Phase 7) review asked for an ADR + guide so
the pattern is authoritative for future modules.

This ADR records the decision; the companion guide
[`docs/guides/suspense-data-loading-guide.md`](../guides/suspense-data-loading-guide.md) gives the concrete
patterns (and complements [`minimizing-useeffect-guide.md`](../guides/minimizing-useeffect-guide.md)).

## Decision

Load data through **Suspense-oriented** mechanisms, never `useEffect`:

1. **Server Components for initial data.** A route's first paint fetches on the server (Server Component
   `async` function or server-side fetch), streaming HTML; no client round-trip for initial data.
2. **TanStack Query (v5) for client-side data.** Interactive/refetchable client data uses `useQuery` /
   `useSuspenseQuery` with shared query-option factories co-located in each module. Mutations use
   `useMutation` with explicit cache invalidation.
3. **React 19 `use()` + `<Suspense>`** to unwrap promises/resources in client components, with a `<Suspense>`
   boundary (loading fallback) and an error boundary (error fallback) wrapping the consumer.

Loading and error states are expressed declaratively via Suspense/error boundaries, not ad-hoc `isLoading`
flags driven by effects. Each bounded-context **module** owns its query contracts (`modules/<context>` query
options / keys), exposed through the module's public barrel.

## Consequences

**Positive:** no fetch waterfalls or effect races; one declarative loading/error model; server-rendered initial
data; testable (mock the query layer, not effects); aligns with the React 19 / App Router direction; the
data-loading contract lives with its bounded context (Phase 7 alignment).

**Negative / costs:** requires discipline around Suspense/error boundary placement and query-key hygiene;
Server vs Client component boundaries (`'use client'`) must be deliberate.

**Enforcement:** the ESLint `no-restricted-syntax` rule blocks `fetch()` in `useEffect`; reviewers reject
effect-driven fetching; new module data access goes through TanStack Query option factories. Violations are a
review blocker, not a suggestion.

## Alternatives considered

- **`useEffect` + `useState` fetching** — rejected: waterfalls, races, duplicated state, untestable (the status
  quo this ADR forbids).
- **A bespoke data-fetching hook layer** — rejected: reinvents TanStack Query (caching, dedup, invalidation,
  Suspense integration) without its maturity.

## References

- `docs/guides/suspense-data-loading-guide.md`, `docs/guides/minimizing-useeffect-guide.md`
- `frontend/CLAUDE.md` (§ "NEVER use useEffect for Data Fetching")
- ADR-009 (domain modular monolith — modules own their contracts)
