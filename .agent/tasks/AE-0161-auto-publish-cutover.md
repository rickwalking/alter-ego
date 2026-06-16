# AE-0161 — Backend: auto-publish cutover — approval != release (BEHAVIOR CHANGE, consent-gated)

Status: Intake
Tier: T2
Priority: High
Type: Task
Area: Backend/Frontend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0161-auto-publish-cutover
Kanban Card: TBD
Created: 2026-06-16
Updated: 2026-06-16

## Goal

Execute the deferred auto-publish cutover: make editorial approval and public release two DISTINCT user actions (approval never auto-publishes). Supersedes the cutover half of AE-0133. BEHAVIOR CHANGE — consent-gated.

## Problem

Phase 6 split the approval!=release CONTRACT (AE-0111) and routed carousel publish through the publishing release command, but kept the existing auto-publish behavior. The roadmap exit gate wants approval and public release to be separate user actions.

## Scope

Make the publishing release command opt-in (not auto-triggered by approval); update the carousel publish flow + the Phase-7 frontend to expose a distinct 'release/publish' action; UPDATE the AE-0125 safety net to assert the NEW behavior. Requires explicit owner consent. THIS IS A BEHAVIOR CHANGE.

## Non-Goals

- Not executed without explicit owner consent (Intake until scheduled).
- Not before the merged Phases 0-7 have been observed in production (roadmap: "after production observation").
- No destructive migration here (that is AE-0162).

## Modularization Alignment (2026-06-16)

Phase 8 of the modularization plan (§Phase 8 "Remove legacy layers and adapters") — the final phase, after
Phases 0-7 merged (PRs #15-#21). Removes the temporary migration scaffolding to zero. Class A (safe cleanup) is
behavior-preserving and holds the existing green gates with down-only ratchets; Class B (auto-publish cutover +
destructive column drop) is consent-gated + drain-gated (ADR-0008). See `docs/plans/phase-8-legacy-removal.md`.

## Acceptance Criteria

- [ ] Approval and public release SHALL be distinct user actions (approval never auto-publishes)
- [ ] The AE-0125 safety net SHALL be updated to assert the new approval!=release flow; new Gherkin scenarios added
- [ ] Explicit owner consent SHALL be recorded before work begins; gates.sh + check-integrity green; publishing contracts KEPT

## Gherkin Scenarios

Defined when scheduled — the cutover CHANGES behavior; scenarios assert the new approval≠release flow and the AE-0125 safety net is updated to the new behavior.

## Dependencies

- Blocks: —
- Blocked by: — (consent-gated; Phases 6/7 merged)
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
