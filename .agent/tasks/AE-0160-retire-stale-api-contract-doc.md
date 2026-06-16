# AE-0160 — Retire stale hand-maintained API-contract doc sections (defer to generated OpenAPI)

Status: Ready
Tier: T1
Priority: High
Type: Task
Area: Docs
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0160-retire-stale-api-contract-doc
Kanban Card: TBD
Created: 2026-06-16
Updated: 2026-06-16

## Goal

Retire the stale hand-maintained sections of docs/architecture/API_CONTRACT.md in favor of the generated docs/architecture/openapi.json (AE-0141), keeping only durable narrative + a pointer to the generated artifact.

## Problem

API_CONTRACT.md is hand-maintained and drifts from the implementation; AE-0141 now generates the OpenAPI spec from the app, making the hand-kept endpoint/schema sections stale and duplicative.

## Scope

Replace the stale endpoint/schema sections with a reference to the generated openapi.json (and the export script); retain genuinely-narrative content (conventions, auth, error model). Docs-only.

## Non-Goals

- No code/behavior change; docs-only.
- Do not delete durable narrative content, only the stale generated-duplicate sections.

## Modularization Alignment (2026-06-16)

Phase 8 of the modularization plan (§Phase 8 "Remove legacy layers and adapters") — the final phase, after
Phases 0-7 merged (PRs #15-#21). Removes the temporary migration scaffolding to zero. Class A (safe cleanup) is
behavior-preserving and holds the existing green gates with down-only ratchets; Class B (auto-publish cutover +
destructive column drop) is consent-gated + drain-gated (ADR-0008). See `docs/plans/phase-8-legacy-removal.md`.

## Acceptance Criteria

- [ ] Stale hand-maintained endpoint/schema sections SHALL be retired in favor of the generated OpenAPI artifact + a pointer
- [ ] Durable narrative (auth/error model/conventions) SHALL be retained
- [ ] Docs-only; no gate impact

## Gherkin Scenarios

Not applicable — legacy-removal cleanup; verified by the green-gate safety net (and, for the Class-B behavior
change, by the updated AE-0125 safety net asserting the new approval≠release flow).

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
