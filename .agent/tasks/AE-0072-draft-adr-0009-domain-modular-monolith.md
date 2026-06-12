# AE-0072 — Draft ADR-0009: adopt domain modular monolith

Status: Dev Complete
Tier: T2
Priority: High
Type: Docs
Area: Cross-cutting
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: docs/ae-0072-adr-0009
Kanban Card: TBD
Created: 2026-06-12
Updated: 2026-06-12

## Goal

Draft `docs/decisions/0009-adopt-domain-modular-monolith.md` (status:
`proposed`, MADR 4.x) carrying every mandatory policy from the approved
plan, including the rollback-track choice that gates Phase 2.5.

## Problem

The plan's four mandatory amendments and its supporting-design decisions
have no ADR home. Phase 2.5 cannot start until the rollback track (full vs
scaled-down) is recorded; the DI and outbox decisions must be explicit so
Phase 1 scaffolding cannot silently lock in alternatives.

## Scope

The ADR must contain, as sections:

- **Operating-context statement** (opens the ADR): transcribed from the
  2026-06-12 interview record — pre-production, single user, no external
  consumers, single-tenant as an explicit constraint; cite the AE-0075
  checkpoint count when available.
- **Rollback track choice**: **scaled-down + migrate-in-place**, decided
  in the interview (see the plan's "Interview Decisions" section): data-
  preserving migrations may rename tables/columns/API with same-phase
  frontend updates; per-migration-window single-writer discipline;
  checkpoint policy is finish-or-restart. State the Phase 2.5 exit-gate
  parameterization that follows.
- **Migration-window definition** (round-4 review finding 4): window =
  schema revision landing → phase exit gate, ceiling 2 calendar weeks;
  exactly one writer per affected table throughout; second-module direct
  writes prohibited even inside a window; mandatory drain-before-migrate
  step (finish on pre-migration code or restart with documented consent).
- **Scope-delta record** (round-4 finding 3): the persona/quality split
  and editorial_operations-as-module deviations are must-haves; include
  the plan's line-item delta table and the revised 11-21 ew / 8-14 month
  totals, plus the Phase-3/month-6 go/no-go milestone.
- **Resource authorization ownership** (amendment 1): context-owned,
  deny-by-default, `ActorContext` on every inbound adapter including
  workers and agent tools.
- **Single writer for `carousel_projects`** (amendment 2): legacy
  coordinator owns the row and `lock_version` during compatibility phases.
- **Rollback and forward-fix policy** (amendment 3): side-effect ledger
  obligations per phase.
- **Outbox delivery semantics** (decision only; implementation is
  Phase 6): durable PostgreSQL outbox, Redis as transport, at-least-once
  with consumer dedup. Phase 0 ships only the reorder fix (AE-0074).
- **DI mechanism**: manual constructor injection with the recorded
  re-evaluation trigger.
- **Migration invariants and rollback criteria** for slices.

## Non-Goals

- ADR status remains `proposed` (acceptance is a human decision).
- No outbox implementation, no code changes.
- Concurrency contract and adversarial matrix live in AE-0073, referenced
  not duplicated.

## Acceptance Criteria

- [ ] `docs/decisions/0009-adopt-domain-modular-monolith.md` exists in
      MADR 4.x format with status `proposed`
- [ ] The ADR's first content section is the operating-context statement
      and it cites the AE-0075 checkpoint count
- [ ] The rollback track is recorded as exactly one of `full` or
      `scaled-down`, with the Phase 2.5 exit-gate consequences spelled out
- [ ] Each of the four mandatory amendments from the plan has a dedicated
      section whose policy is stated normatively (SHALL language), not as
      a summary of the plan
- [ ] The DI section names manual constructor injection and quotes the
      re-evaluation trigger condition
- [ ] The outbox section states Redis is transport, not proof of durable
      consumption, and explicitly defers implementation to Phase 6
- [ ] WHEN the ADR is added THE root `CLAUDE.md` ADR list SHALL include
      ADR-0009 with a matching link (file `0009-adopt-domain-modular-monolith.md`,
      per the `NNNN-short-title.md` convention)
- [ ] The ADR records the two conditional Phase 2.5 re-escalation gates
      from the plan's final recommendation (checkpoint payloads prove
      class-path-dependent; `lock_version` activation strategy changes)
- [ ] The migration-invariants section enumerates the nine rollout/rollback
      slice rules from the plan's "Rollout and Rollback" section
- [ ] All glossary terms used by the ADR resolve against
      `docs/architecture/domain-glossary.md` (AE-0071)

## Gherkin Scenarios

Not applicable — documentation only; no runtime behavior changes.

## Delta

### ADDED

- `docs/decisions/0009-adopt-domain-modular-monolith.md`

### MODIFIED

- `CLAUDE.md` (ADR index list)

### REMOVED

- None

## Affected Areas

- Backend: none (reference only)
- Frontend: none
- Database: none
- API: none
- Tests: none
- Docs: new ADR + CLAUDE.md index
- Prompts/LLM: none
- Observability: none
- Deployment: none

## Dependencies

- Blocks: Phase 2.5 start
- Blocked by: AE-0071 (glossary), AE-0075 (checkpoint count for the
  operating-context statement)
- Related: AE-0070; AE-0073 (its final text references ADR section
  numbers but drafting may start early — soft dependency only)

## Implementation Plan

1. Copy MADR 4.x skeleton from an existing ADR (0007/0008 style).
2. Write the operating-context statement from AE-0075 evidence plus
   deployment facts; decide and record the track.
3. Transcribe the four amendment policies into normative sections.
4. Update the CLAUDE.md ADR index.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-12 00:00

Ticket created by planner.

## Files Touched

- docs/decisions/0009-adopt-domain-modular-monolith.md (new)
- CLAUDE.md (ADR index +1 line)

## Test Evidence

Docs-only ticket; no runtime tests. Verified: CLAUDE.md ADR index now links
ADR-0009; all glossary terms used resolve against domain-glossary.md; all 10 ACs
self-checked PASS (see dev-summary).

## QA Report

Pending.

## Decision Log

Pending.

## Blockers

None.

## Final Summary

Pending.
