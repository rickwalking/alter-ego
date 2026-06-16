# AE-0152 — Phase 8 epic: Remove legacy layers and adapters

Status: Ready
Tier: T3
Priority: High
Type: Task
Area: Cross-cutting
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0152-phase8-epic-legacy-removal
Kanban Card: TBD
Created: 2026-06-16
Updated: 2026-06-16

## Goal

Epic tracking the removal of the temporary modularization scaffolding (shims, re-exports, exact import-linter exceptions, grandfathered baselines, stale API-contract docs) and the two consent-gated deferred changes (auto-publish cutover + embedded-column drop). Tracks AE-0153..AE-0162.

## Problem

Phases 0-7 left compatibility scaffolding (frontend @/features shims, backend re-exports, 35 .importlinter ignore_imports, grandfathered import baselines) and deferred two behavior/destructive changes. The roadmap's final phase removes them.

## Scope

Coordinate the Phase 8 vertical slices: Class A (safe cleanup) AE-0153..0160 + Class B (consent-gated) AE-0161..0162. Supersedes the umbrella deferral records AE-0133 (->0161/0162) and AE-0143 (->0153-0157).

## Non-Goals

- No table-splitting for independent ownership (no measurable value; roadmap-excluded).
- Class B does not start without explicit owner consent.

## Modularization Alignment (2026-06-16)

Phase 8 of the modularization plan (§Phase 8 "Remove legacy layers and adapters") — the final phase, after
Phases 0-7 merged (PRs #15-#21). Removes the temporary migration scaffolding to zero. Class A (safe cleanup) is
behavior-preserving and holds the existing green gates with down-only ratchets; Class B (auto-publish cutover +
destructive column drop) is consent-gated + drain-gated (ADR-0008). See `docs/plans/phase-8-legacy-removal.md`.

## Acceptance Criteria

- [ ] All Class-A sub-tickets (AE-0153..0160) SHALL reach Review behavior-preservingly with green gates
- [ ] Class-B sub-tickets (AE-0161/0162) SHALL remain Intake until explicit owner consent
- [ ] At epic close: no production import uses legacy module paths; architecture rules pass without broad ignores; the destructive drop (if executed) is proven reversible + drain-gated

## Gherkin Scenarios

Not applicable — legacy-removal cleanup; verified by the green-gate safety net (back-end gates.sh + check-integrity + arch-ratchet; front-end typecheck/lint/boundaries/url/circular/tests/build).

## Dependencies

- Blocks: AE-0153..AE-0162
- Blocked by: —
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
