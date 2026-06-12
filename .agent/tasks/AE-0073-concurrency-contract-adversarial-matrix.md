# AE-0073 — Concurrency contract draft and adversarial test matrix skeleton

Status: Ready
Tier: T2
Priority: Medium
Type: Docs
Area: Backend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: docs/ae-0073-concurrency-adversarial-drafts
Kanban Card: TBD
Created: 2026-06-12
Updated: 2026-06-12

## Goal

Produce the two Phase 0 design drafts the plan timeboxes at one day each:
the concurrency contract and the adversarial test matrix skeleton.

## Problem

The round-2 skeptical review found that deferred designs with no phase
owner get silently descoped. The plan now assigns both drafts to Phase 0;
they parameterize Phase 2.5's `lock_version` tests and every phase's exit
gate rows.

## Scope

- `docs/architecture/concurrency-contract.md` draft covering the plan's
  required fields: expected aggregate/legacy-row version, idempotency key
  for retried operations, operations requiring serialization, conflict
  response and client retry behavior, artifact build deduplication,
  projection freshness, stale-content publication rule.
- `docs/architecture/adversarial-test-matrix.md` skeleton: the plan's ten
  adversarial categories as rows, phases as columns, each cell marked
  required/n-a; no test code.

## Non-Goals

- No test implementation (cells are filled by each phase's exit gate work).
- No `lock_version` enforcement code (Phase 2.5, per the recorded rollout
  strategy).

## Acceptance Criteria

- [ ] `docs/architecture/concurrency-contract.md` exists and addresses all
      seven required fields from the plan's "Concurrency contract" section
- [ ] The contract states the conflict response shape for a stale
      `lock_version` write (HTTP status and error payload) in EARS form:
      WHEN a command carries a stale expected version THE API SHALL return
      409 with a machine-readable conflict body — **decided, not draft**
      (2026-06-12 interview: 409 + UI refresh prompt + idempotency keys
      on workflow commands)
- [ ] `docs/architecture/adversarial-test-matrix.md` exists with all ten
      categories from the plan's "Adversarial test matrix" section as
      rows, each row citing the plan's category text verbatim so coverage
      is mechanically checkable
- [ ] Every matrix cell for Phases 2 through 8 **including Phase 2.5** is
      explicitly marked `required` or `n/a` with a one-line reason for
      each `n/a`
- [ ] Both documents link to ADR-0009 and the glossary; no term conflicts
      with `docs/architecture/domain-glossary.md`

## Gherkin Scenarios

Not applicable — documentation only; the contract's scenarios become
executable in Phase 2.5 tickets.

## Delta

### ADDED

- `docs/architecture/concurrency-contract.md`
- `docs/architecture/adversarial-test-matrix.md`

### MODIFIED

- None

### REMOVED

- None

## Affected Areas

- Backend: none (reference only)
- Frontend: none
- Database: none
- API: none (contract is normative for later phases)
- Tests: none yet (matrix governs later phases)
- Docs: two new architecture documents
- Prompts/LLM: none
- Observability: none
- Deployment: none

## Dependencies

- Blocks: Phase 2.5 ticket writing
- Blocked by: none (drafts may start before AE-0072 merges; final text
  must reference the ADR section numbers)
- Related: AE-0070, AE-0072, AE-0075

## Implementation Plan

1. Draft the concurrency contract from the plan's required-fields list and
   AE-0075's `lock_version` distribution facts.
2. Build the matrix skeleton; mark Phase 2 (Knowledge) and Phase 2.5 rows
   first since they execute soonest.

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
