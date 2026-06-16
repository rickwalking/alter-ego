# AE-0155 — Frontend: route-page thinning (app pages -> thin composition)

Status: Ready
Tier: T2
Priority: High
Type: Task
Area: Frontend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0155-frontend-route-page-thinning
Kanban Card: TBD
Created: 2026-06-16
Updated: 2026-06-16

## Goal

Reduce app/**/page.tsx to thin composition components over module hooks/contracts, where it can be done without behavior risk (Phase 7 kept pages as-is).

## Problem

Phase 7 kept route pages unchanged to stay behavior-preserving; some pages still contain data/composition logic that belongs in module hooks, violating the 'route pages are thin composition' exit-gate intent.

## Scope

For pages with extractable data/composition logic, move it into the owning module (hooks/contracts) and leave the page as thin composition; keep App Router URLs + segment config + rendered output byte-identical. Skip pages where thinning risks behavior.

## Non-Goals

- No App Router URL or segment-config change; no observable behavior change.
- No exhaustive rewrite — only safe extractions.

## Modularization Alignment (2026-06-16)

Phase 8 of the modularization plan (§Phase 8 "Remove legacy layers and adapters") — the final phase, after
Phases 0-7 merged (PRs #15-#21). Removes the temporary migration scaffolding to zero. Class A (safe cleanup) is
behavior-preserving and holds the existing green gates with down-only ratchets; Class B (auto-publish cutover +
destructive column drop) is consent-gated + drain-gated (ADR-0008). See `docs/plans/phase-8-legacy-removal.md`.

## Acceptance Criteria

- [ ] Targeted route pages SHALL become thin composition over module hooks (no inline data logic)
- [ ] App Router URLs + segment config unchanged (url:check 26); rendered output byte-identical
- [ ] typecheck + lint + 822 tests + build green; boundary 0

## Gherkin Scenarios

Not applicable — legacy-removal cleanup; verified by the green-gate safety net (back-end gates.sh + check-integrity + arch-ratchet; front-end typecheck/lint/boundaries/url/circular/tests/build).

## Dependencies

- Blocks: —
- Blocked by: AE-0153
- Related: AE-0152

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-16

Ticket created by planner (Phase 8 breakdown).

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
