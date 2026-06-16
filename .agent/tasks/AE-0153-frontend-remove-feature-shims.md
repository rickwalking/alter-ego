# AE-0153 — Frontend: remove @/features/* re-export shims + delete src/features/ + drop _example anchor

Status: Ready
Tier: T1
Priority: High
Type: Task
Area: Frontend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0153-frontend-remove-feature-shims
Kanban Card: TBD
Created: 2026-06-16
Updated: 2026-06-16

## Goal

Delete the 12 src/features/* re-export shim dirs (left by Phase 7 for compatibility) and the modules/_example boundary anchor, once no production/test import references them.

## Problem

Phase 7 migrated features into modules/<context> but left thin @/features/* re-export shims so consumers kept resolving. With all consumers on @/modules/<context>, the shims are dead compatibility scaffolding; the _example anchor is no longer needed (real module barrels exist).

## Scope

Confirm (grep + typecheck + lint) NO import (incl. tests/stories/app) references any @/features/* path or modules/_example; then delete src/features/ entirely + modules/_example. Behavior-preserving. Keep all frontend gates green; boundary baseline stays 0.

## Non-Goals

- No behavior/UI/URL change; no component logic moved (Phase 7 already moved it).
- No new module work.

## Modularization Alignment (2026-06-16)

Phase 8 of the modularization plan (§Phase 8 "Remove legacy layers and adapters") — the final phase, after
Phases 0-7 merged (PRs #15-#21). Removes the temporary migration scaffolding to zero. Class A (safe cleanup) is
behavior-preserving and holds the existing green gates with down-only ratchets; Class B (auto-publish cutover +
destructive column drop) is consent-gated + drain-gated (ADR-0008). See `docs/plans/phase-8-legacy-removal.md`.

## Acceptance Criteria

- [ ] A grep/typecheck proof SHALL show zero importers of any @/features/* path or modules/_example
- [ ] src/features/ and modules/_example SHALL be deleted; no dangling references
- [ ] The boundary checker SHALL run GREEN after _example removal (real module barrels satisfy the scanner; config does not require a non-empty modules/ glob)
- [ ] typecheck + lint (boundaries 0/0 + url 26 + circular 0 + component-types) + 822 tests + build green

## Gherkin Scenarios

Not applicable — legacy-removal cleanup; verified by the green-gate safety net (back-end gates.sh + check-integrity + arch-ratchet; front-end typecheck/lint/boundaries/url/circular/tests/build).

## Dependencies

- Blocks: AE-0154, AE-0155, AE-0156
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
