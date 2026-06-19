# AE-0238 — Block duplicate ticket IDs + harden next_ticket_id allocation across git refs

Status: Review
Tier: T2
Priority: High
Type: Quality
Area: Cross-cutting
Owner: Unassigned
Agent Lane: developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-18
Updated: 2026-06-18

## Goal

Make duplicate ticket IDs impossible to land silently: fail the validation gate on a
collision (instead of merely warning), and stop the local-only allocator from minting
IDs that already exist on other branches.

## Problem

Failure class **FC-2** (kaizen session-2026-06-18c). `next_ticket_id`
(`scripts/agent_tasks/create_ticket.py:24`) allocates the next ID by globbing
`AE-*.md` in the **local working tree only** and taking max+1. IDs that live on an
unmerged branch are invisible, so branching off an older base re-allocates colliding
IDs. This has happened **twice**: AE-0145..0148 collided and had to be renumbered to
AE-0224..0227, and AE-0228 was a near-miss this session. The existing
`_warn_duplicate_ids()` in `validate_all_tickets.py` detects collisions but only
**prints a WARNING (exit 0)** — deliberately left non-blocking by AE-0181 ("renumbering
tracked separately"). Two real collisions now override that decision.

Reports: `.agent/reports/kaizen-session-2026-06-18c.{signal,plan,skeptical-review}.md`.

## Scope

- `scripts/agent_tasks/validate_all_tickets.py` — promote dup-ID detection to blocking.
- `scripts/agent_tasks/create_ticket.py` — `next_ticket_id` consults git refs for the
  global max ID.
- `backend/tests/unit/agent_tasks/` — seeded-violation test.

## Non-Goals

- No change to the ID format (`AE-####`) or to historical IDs.
- No centralized/remote ID-reservation service (recorded as a future option only).

## Acceptance Criteria

- [x] `validate_all_tickets.py` **exits 1** when two ticket files share one `AE-####`
      ID (promote `_warn_duplicate_ids` to a blocking error; keep the actionable
      remediation message). Done: `_blocking_duplicate_ids` folds into the exit code.
- [x] **Seeded-violation proof:** a test creates two ticket files with the **same** ID
      and **no other validation errors**, and asserts the validator exits **1** (the
      pure 0→1 boundary the critic flagged). A single-ID control case still exits 0.
      Done: `test_validate_all_tickets.py`.
- [x] `next_ticket_id` computes the next ID from the **max across all local ticket
      files AND all git refs** (`git rev-list --all --objects`), so allocating off an
      older base can no longer reuse an ID minted on another branch. Degrades
      gracefully (falls back to local-only) when git is unavailable.
- [x] The **residual parallel-PR window is documented** in the `create_ticket.py`
      module docstring: two concurrent PRs each minting the same new ID both pass their
      own merge-ref CI; the collision is caught on the push-to-`main` run (post-merge)
      by the now-blocking gate. Full pre-merge prevention would need centralized
      reservation (out of scope).
- [x] `validate_all_tickets.py` runs green on the real tree (`All 236 ticket(s) OK`).

## Gherkin Scenarios

```gherkin
Feature: Duplicate ticket IDs fail the gate

  Scenario: Two files share an ID
    Given two ticket files both numbered AE-0500 with no other errors
    When validate_all_tickets.py runs
    Then it prints the duplicate-ID remediation message
    And it exits with status 1

  Scenario: Allocator sees IDs on other branches
    Given AE-0600 exists only on an unmerged branch
    When next_ticket_id runs on a base that lacks AE-0600 locally
    Then it returns AE-0601 (not AE-0600)
```

## Delta

### ADDED
- Seeded duplicate-ID test under `backend/tests/unit/agent_tasks/`.
- Git-ref scan in `next_ticket_id`.

### MODIFIED
- `_warn_duplicate_ids` → blocking (feeds the exit code).

### REMOVED
- The "non-blocking by design" stance from AE-0181 (superseded; note it in the code).

## Affected Areas

- Backend: agent_tasks scripts + tests.
- Frontend: none.
- Database: none.
- API: none.
- Tests: `backend/tests/unit/agent_tasks/`.
- Docs: short note on the residual parallel-PR window.
- Deployment: none (the gate runs in CI; no runtime impact).

## Dependencies

- Blocks: prevents the AE-0145..0148-style renumber toil recurring.
- Blocked by: none (independent of AE-0237, but both touch agent_tasks — sequence to
  avoid churn).
- Related: AE-0181 (non-blocking dup-ID warning, superseded here), AE-0203 (the single
  required `ci-gate` check that carries `agent-gate`).

## Implementation Plan

1. In `validate_all_tickets.main`, make duplicates increment the blocking counter (or
   return non-zero) — keep the message.
2. Add the seeded test (two same-ID files, no other errors → exit 1; control → exit 0).
3. Harden `next_ticket_id` to union local glob + a git-ref scan for the max ID; fall
   back to local-only when not in a git repo.
4. Document the residual window in the script docstring + a one-line note in the
   agentic-delivery docs.

## Test Classification (CLAUDE.md AE-0153 / AE-0180)

- **CI/tooling ticket** — promotes a static-analysis/validation rule. **Unit tests +
  the seeded-violation test suffice; no `.feature` required.**
- **No public/user-visible behavior change** (the workflow tooling gets stricter; no
  product behavior changes).
- **Seeded-violation test:** two same-ID files → exit 1 (proves the rule fires).
- **Affected gates:** `agent-ticket-hygiene.yml` + `ci-gate` `agent-gate` job.
- Reviewer/QA to sign off on the no-`.feature` classification.

## QA Checklist

- [x] Security reviewed
- [x] Code quality reviewed
- [x] Acceptance criteria validated
- [x] Edge cases tested (dup with/without other errors; git unavailable)
- [x] Orphan/unfinished code checked

## Progress Log

### 2026-06-18 21:00

Created by kaizen session-2026-06-18c (FC-2). Cold-critic (opencode) surfaced the
parallel-PR merge-ref race (gate catches branch-vs-main pre-merge but parallel-vs-
parallel only post-merge), and the precise 0→1 seeded-test boundary. Allocator
hardening promoted from optional to a required AC to attack the root cause.

### 2026-06-18 23:45

Implemented (developer-skill wave). Dup-id check now blocking; `next_ticket_id`
unions local glob + `git rev-list --all --objects`; residual window documented.
27 passed; real-tree validate green.

### 2026-06-18 — wave QA round 1 fix (F-1, minor)

External QA flagged that the dup-id test pinned only exit 0-vs-nonzero (a
`len(dupes)*k` mutant would survive). Added `test_blocking_duplicate_ids_returns_exact_count`
(asserts the exact dup-id count) + a stdout assertion on the remediation message.

## Files Touched

- `scripts/agent_tasks/validate_all_tickets.py` — `_warn_duplicate_ids` →
  `_blocking_duplicate_ids` (returns dup count, folded into the exit code).
- `scripts/agent_tasks/create_ticket.py` — `_git_max_ticket_num` (git-ref scan via
  `git rev-list --all --objects`) + `next_ticket_id` unions local + git max;
  module docstring documents the residual parallel-PR window.
- `backend/tests/unit/agent_tasks/test_validate_all_tickets.py` (NEW) — seeded
  0→1 boundary (two same-id files, no other errors → exit 1; unique → exit 0).
- `backend/tests/unit/agent_tasks/test_create_ticket.py` — git-ref allocator test
  (AE-0600 only on a feature ref → allocator returns AE-0601).

## Test Evidence

```
$ uv run pytest tests/unit/agent_tasks/ -q
27 passed, 1 skipped
$ uv run python scripts/agent_tasks/validate_all_tickets.py
All 236 ticket(s) OK
```

Seeded-violation proof: `test_duplicate_ids_fail_with_no_other_errors` asserts the
validator exits 1 on two same-id files that are otherwise valid (the precondition
asserts no other errors), pinning the pure 0→1 flip.

## QA Report

External wave QA (wave-kaizen-1): **PASS** over 2 rounds (round 1 WARN with one
minor finding F-1, resolved; confirmation round PASS, 0 findings). See
`.agent/reports/AE-0238.qa.md` → `.agent/reports/wave-kaizen-1.qa.md`.


## Decision Log

- **Critic [BLOCKER] parallel-PR race** — ACCEPTED as a documented residual. The
  blocking gate fully prevents branch-vs-main collisions pre-merge and catches
  parallel-vs-parallel post-merge on the `main` push run. Root-cause mitigation =
  the git-ref-aware allocator (added as an AC). Full pre-merge prevention would
  require centralized ID reservation — recorded as a future option, out of scope.
- **Critic [WARN] exit-code wiring** — ACCEPTED: the seeded test uses two same-ID
  files with **no other validation errors** to prove the exit code flips 0→1 (not
  masked by an unrelated failure).
- **Supersedes AE-0181's non-blocking choice** — justified by two real collisions; the
  attribution check AE-0181 added stays in place as defense in depth.

## Blockers

None.

## Final Summary

Pending.
