# AE-0157 — Reconcile OpenAPI/Zod schema drifts to 0 + flip the drift check to blocking

Status: Ready
Tier: T2
Priority: High
Type: Task
Area: Frontend/CI
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0157-schema-drift-blocking
Kanban Card: TBD
Created: 2026-06-16
Updated: 2026-06-16

## Goal

Reconcile the 24 advisory OpenAPI/Zod schema-drift findings (AE-0141) to 0, then flip the schema-drift check from advisory to blocking in CI.

## Problem

AE-0141 shipped the drift check as advisory with 24 pre-existing frontend Zod vs backend OpenAPI divergences (nullability, missing/extra fields). The exit gate wants it blocking once clean.

## Scope

Reconcile each of the 24 drifts behavior-preservingly (align the frontend Zod schema to the actual API contract, or document an intentional divergence as an exclusion); regenerate the OpenAPI artifact; flip check:schema-drift to --strict / blocking in gates.sh + CI. Validate that genuine fixes don't change runtime parsing behavior.

## Non-Goals

- No backend API change (align the frontend to the API, not vice-versa, unless a real backend bug is found -> separate ticket).
- No silencing drifts by widening ignores without justification.

## Modularization Alignment (2026-06-16)

Phase 8 of the modularization plan (§Phase 8 "Remove legacy layers and adapters") — the final phase, after
Phases 0-7 merged (PRs #15-#21). Removes the temporary migration scaffolding to zero. Class A (safe cleanup) is
behavior-preserving and holds the existing green gates with down-only ratchets; Class B (auto-publish cutover +
destructive column drop) is consent-gated + drain-gated (ADR-0008). See `docs/plans/phase-8-legacy-removal.md`.

## Acceptance Criteria

- [ ] The 24 drift findings SHALL reach 0 (fixed or justified-excluded)
- [ ] The schema-drift check SHALL be flipped to blocking (--strict) in gates.sh + CI and pass
- [ ] typecheck + lint + 822 tests + build green; no runtime parsing behavior change

## Gherkin Scenarios

Not applicable — legacy-removal cleanup; verified by the green-gate safety net (and, for the Class-B behavior
change, by the updated AE-0125 safety net asserting the new approval≠release flow).

## Dependencies

- Blocks: —
- Blocked by: AE-0156
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
