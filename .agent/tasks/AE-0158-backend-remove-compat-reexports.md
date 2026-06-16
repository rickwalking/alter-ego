# AE-0158 — Backend: remove dead compatibility re-exports/shims; ratchet import baselines down

Status: Ready
Tier: T2
Priority: High
Type: Task
Area: Backend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0158-backend-remove-compat-reexports
Kanban Card: TBD
Created: 2026-06-16
Updated: 2026-06-16

## Goal

Delete backend compatibility re-exports / object-identity shims where the module facade is now the sole import path, and ratchet the grandfathered import baselines (application->infra, api->infra, get_container, commit-sites) DOWN to their true floor.

## Problem

The phased extraction left re-export shims + grandfathered import-baseline pairs so legacy paths kept resolving. With ownership in modules, many are dead; the baselines over-count vs reality.

## Scope

Grep for re-exports/shims with no remaining external importer and delete them; re-run import_baseline.py to ratchet the baselines DOWN to current; keep lint-imports + import_baseline.py --check green at the lower numbers. Behavior-preserving.

## Non-Goals

- No runtime behavior change; only dead-path removal + baseline ratchet-down.
- No NEW imports; no raising any baseline.

## Modularization Alignment (2026-06-16)

Phase 8 of the modularization plan (§Phase 8 "Remove legacy layers and adapters") — the final phase, after
Phases 0-7 merged (PRs #15-#21). Removes the temporary migration scaffolding to zero. Class A (safe cleanup) is
behavior-preserving and holds the existing green gates with down-only ratchets; Class B (auto-publish cutover +
destructive column drop) is consent-gated + drain-gated (ADR-0008). See `docs/plans/phase-8-legacy-removal.md`.

## Acceptance Criteria

- [ ] Dead backend re-exports/shims (zero external importers) SHALL be removed
- [ ] import_baseline.py baselines SHALL ratchet DOWN to the true current floor; --check PASS
- [ ] gates.sh backend 14/0/3 + check-integrity 0 blockers + mypy + lint-imports green

## Gherkin Scenarios

Not applicable — legacy-removal cleanup; verified by the green-gate safety net (back-end gates.sh + check-integrity + arch-ratchet; front-end typecheck/lint/boundaries/url/circular/tests/build).

## Dependencies

- Blocks: AE-0159, AE-0160
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
