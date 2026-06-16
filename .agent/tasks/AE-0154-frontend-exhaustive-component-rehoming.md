# AE-0154 — Frontend: exhaustive business-component re-homing; ratchet component-type-location down

Status: Ready
Tier: T2
Priority: High
Type: Task
Area: Frontend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0154-frontend-exhaustive-component-rehoming
Kanban Card: TBD
Created: 2026-06-16
Updated: 2026-06-16

## Goal

Move any remaining domain-named components still in components/atoms|molecules|organisms into their owning module (Phase 7 did the clear-cut ones); keep generic Neon* primitives atomic. Ratchet the component-type-location baseline (57) down toward 0 by moving inline types to colocated types.ts.

## Problem

Phase 7 re-homed the obvious business components (PersonaCard/RubricCard/BlogPostCard/KanbanBoard) but left ambiguous/remaining domain components in the global atomic folders, and 57 inline component/hook types remain grandfathered.

## Scope

Identify remaining domain-owned components in components/* and move them to their module + barrel (with stories/tests); generic Neon* stay. Move inline object-shape types to colocated types.ts and ratchet component-type-location-baseline.json DOWN. Behavior-preserving.

## Non-Goals

- Generic Neon* primitives stay in components/* (not domain-owned).
- No behavior/UI change; type-only + relocation.

## Modularization Alignment (2026-06-16)

Phase 8 of the modularization plan (§Phase 8 "Remove legacy layers and adapters") — the final phase, after
Phases 0-7 merged (PRs #15-#21). Removes the temporary migration scaffolding to zero. Class A (safe cleanup) is
behavior-preserving and holds the existing green gates with down-only ratchets; Class B (auto-publish cutover +
destructive column drop) is consent-gated + drain-gated (ADR-0008). See `docs/plans/phase-8-legacy-removal.md`.

## Acceptance Criteria

- [ ] Remaining domain components SHALL live in their owning module behind the barrel; generic Neon* stay atomic
- [ ] component-type-location baseline SHALL ratchet DOWN (toward 0); 0 new
- [ ] typecheck + lint + 822 tests + build + build-storybook green; boundary 0

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
