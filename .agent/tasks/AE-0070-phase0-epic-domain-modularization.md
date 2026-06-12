# AE-0070 — Phase 0 epic: language, constraints, and evidence for domain modularization

Status: Ready
Tier: T3
Priority: High
Type: Epic
Area: Cross-cutting
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: N/A (epic; sub-tickets carry branches)
Kanban Card: TBD
Created: 2026-06-12
Updated: 2026-06-12

## Goal

Complete Phase 0 of the approved domain modularization plan: shared
language, ADR-0009 draft with the rollback-track choice, the immediate
event-ordering fix, and the evidence inventories that gate Phase 2.5.

## Problem

The modularization plan (`.agent/reports/domain-modularization.options.md`)
passed its round-3 skeptical review (`PROCEED_WITH_CAUTION`, no blockers)
and authorizes Phase 0 only. Phase 0 produces the decisions and evidence
that every later phase depends on; without it, no module work may start.

## Scope

- Track sub-tickets AE-0071 through AE-0078 to completion.
- Own the Phase 0 time budget published in
  `docs/plans/domain-modularization-phase0.md`; if any item overflows the
  2-week box, open a named Phase 0b ticket instead of extending silently.
- Confirm the Phase 0 exit gate from the plan: context map accepted and
  the glossary terms unambiguous.

## Non-Goals

- No production module extraction, package moves, or Import Linter
  contract changes (Phase 1+).
- No `carousel_projects` field ownership map (Phase 2.5).
- No database migrations.

## Acceptance Criteria

- [ ] WHEN AE-0071 through AE-0078 are Done THE epic SHALL list each
      sub-ticket's outcome in its Final Summary
- [ ] WHEN Phase 0 completes THE plan's Phase 0 exit gate (context map
      accepted; `Carousel`, `EditorialProject`, `BlogPost`, `Publication`,
      `Workflow`, `Source`, and status terms unambiguous) SHALL be recorded
      as met in the Decision Log with a pointer to the glossary
- [ ] WHEN any sub-ticket exceeds its budget in
      `docs/plans/domain-modularization-phase0.md` THE overflow SHALL be
      moved to a named Phase 0b ticket and recorded in the Decision Log
- [ ] WHEN the epic closes THE Phase 2.5 preconditions (rollback track
      recorded in ADR-0009; checkpoint serialization confirmed portable or
      escalation raised) SHALL each be marked met or escalated
- [ ] WHEN AE-0075 returns a CLASS-PATH-DEPENDENT verdict or AE-0072
      records a changed `lock_version` activation strategy THE epic SHALL
      record the Phase 2.5 re-escalation in the Decision Log per the
      plan's final-recommendation gates
- [ ] `uv run python scripts/agent_tasks/validate_all_tickets.py` passes
      with 0 errors

## Gherkin Scenarios

Not applicable — coordination epic; behavior changes are specified in
sub-tickets (AE-0074, AE-0076).

## Delta

### ADDED

- `docs/plans/domain-modularization-phase0.md` (epic plan, this breakdown)

### MODIFIED

- `.agent/BOARD.md` as sub-tickets progress

### REMOVED

- None

## Affected Areas

- Backend: via AE-0074, AE-0075, AE-0076, AE-0078
- Frontend: via AE-0076, AE-0077
- Database: none
- API: none (behavior preserved; AE-0074 changes internal ordering only)
- Tests: via sub-tickets
- Docs: via AE-0071, AE-0072, AE-0073, AE-0075, AE-0077, AE-0078
- Prompts/LLM: none
- Observability: via AE-0074 (event emission ordering)
- Deployment: none

## Dependencies

- Blocks: all Phase 1+ modularization work
- Blocked by: none
- Related: AE-0040 (epic; AE-0044/0045/0046 touch carousel service files —
  coordinate if started in parallel), domain-modularization reports r1-r3

## Implementation Plan

1. Validate sub-tickets (architect validate) and move them to Ready.
2. Execute parallel-safe tickets first (AE-0074, AE-0075, AE-0076,
   AE-0077, AE-0078), then AE-0071 → AE-0072 → AE-0073.
3. Confirm the Phase 0 exit gate and Phase 2.5 preconditions; close epic.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-12 00:00

Ticket created by planner from the approved Phase 0 scope.

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
