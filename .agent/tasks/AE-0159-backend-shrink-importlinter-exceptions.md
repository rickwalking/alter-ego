# AE-0159 — Backend: shrink .importlinter ignore_imports exceptions; delete dead global layer files

Status: Ready
Tier: T2
Priority: High
Type: Task
Area: Backend/CI
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0159-backend-shrink-importlinter-exceptions
Kanban Card: TBD
Created: 2026-06-16
Updated: 2026-06-16

## Goal

Shrink the 35 .importlinter exact ignore_imports exceptions as their underlying violations reach zero, and delete global application/domain/infrastructure files whose ownership has fully moved into modules.

## Problem

The phased extraction grandfathered 35 exact import exceptions + left some global layer files that modules have superseded. The exit gate requires architecture rules to pass WITHOUT broad ignores.

## Scope

For each ignore_imports exception, verify the violation no longer occurs (the edge moved behind a facade/ACL) and remove the exception; delete global layer files with no remaining importer; regenerate .importlinter via render_importlinter; keep lint-imports green with fewer exceptions. Behavior-preserving.

## Non-Goals

- No runtime behavior change; only exception/file removal once truly dead.
- Keep the legitimate AE-0126 object-identity re-export shims if still required.

## Modularization Alignment (2026-06-16)

Phase 8 of the modularization plan (§Phase 8 "Remove legacy layers and adapters") — the final phase, after
Phases 0-7 merged (PRs #15-#21). Removes the temporary migration scaffolding to zero. Class A (safe cleanup) is
behavior-preserving and holds the existing green gates with down-only ratchets; Class B (auto-publish cutover +
destructive column drop) is consent-gated + drain-gated (ADR-0008). See `docs/plans/phase-8-legacy-removal.md`.

## Acceptance Criteria

- [ ] Each removable .importlinter ignore_imports exception SHALL be deleted (violation verified gone); count strictly decreases
- [ ] Dead global layer files (zero importers) SHALL be removed
- [ ] .importlinter SHALL be regenerated via render_importlinter (not hand-edited); lint-imports KEEPS all contracts (incl. the per-module identity/conversation/knowledge facade contracts) at the reduced ignore count
- [ ] arch-ratchet (import_baseline.py --check) + gates.sh + check-integrity green

## Gherkin Scenarios

Not applicable — legacy-removal cleanup; verified by the green-gate safety net (back-end gates.sh + check-integrity + arch-ratchet; front-end typecheck/lint/boundaries/url/circular/tests/build).

## Dependencies

- Blocks: —
- Blocked by: AE-0158
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
