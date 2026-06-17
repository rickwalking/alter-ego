# Kaizen Report — session-learnings-3 (2026-06-17)
Mode: sweep (retrospective) | Scope: executing the remaining frontend-debt epics

## This pass
AE-0186 (refactor 3 giants → thin composition, 884 tests unchanged), AE-0188 Ph2
(safe lint fixes 251→245), AE-0187 (Suspense pattern + baseline + 1 exemplar).
All via dev→QA subagents; each converged with tests green, zero suppressions.

## Learning Classes (ranked)

| # | Learning | Evidence | Severity |
|---|----------|----------|----------|
| L1 | Most of the "327 lint warnings" are NOT debt — they are legitimate runtime guards (`no-unnecessary-condition` on API/SSE/array-bounds) and intentional `||` falsy-coalescing. Only ~6/251 were safely fixable. | AE-0188 Ph2 | High |
| L2 | Silent error-swallowing is a real latent bug class: `useDocuments` defaulted fetch errors to `[]` (empty state), hiding failures. Suspense+ErrorBoundary surfaced it. | AE-0187 exemplar | High |
| L3 | A blanket "warnings→errors" lock-in (AE-0166 / AE-0188 Ph3) would mis-fire on the legit guards in L1 — needs per-rule, post-burndown promotion, not a global flip. | L1 + AE-0188 | Med |
| L4 | Large refactors are safe to delegate when behavior-based tests are the gate; snapshot-only assertions are not enough. | AE-0186 (884 tests held) | Info |

## Proposals (for human review — NOT auto-created)
- **K1:** Re-tune rather than burn-down — `no-unnecessary-condition` is noisy against
  runtime-validated boundaries; consider scoping it off API/SSE payload types or
  accepting it as advisory. (Refines AE-0166's "warnings→errors" ambition.)
- **K2 (real-bug hunt):** audit for the L2 pattern — `catch → return []/{}/null` that
  swallows fetch errors into empty states. Likely several beyond `useDocuments`.

## Rejected (would loosen): none. (Promoting legit-guard rules to error to "win" the
## count would force eslint-disable churn — explicitly avoided.)
