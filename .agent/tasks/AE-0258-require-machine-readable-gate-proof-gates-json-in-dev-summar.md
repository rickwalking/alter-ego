# AE-0258 — require machine-readable gate proof (gates_json) in dev-summary and qa report

Status: Review
Tier: T2
Priority: High
Type: Quality
Area: Cross-cutting
Owner: Unassigned
Agent Lane: architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-19
Updated: 2026-06-19

## Goal

Make "the full QA gate set was actually run" **mechanically checkable** at the ticket
boundary, so a ticket cannot advance on a prose "all green" or a delegated agent's
unverified self-report.

## Problem

`scripts/agent_tasks/schema.py` gates the `Dev Complete` transition on a non-scaffold
`.dev-summary.md` + acceptance criteria, and the `Review` transition on a non-empty,
id-attributed `.qa.md` (AE-0181) — **neither checks whether the gate set passed**. A
hand-written "all green" satisfies both. This let the dev loop declare tickets Dev
Complete on a gate **subset** and on a subagent's self-reported (and once **false** —
net-new `# type: ignore`) "0 blockers". `scripts/ci/gates.sh:321` already prints a
machine-readable `GATES_JSON: {"pass":N,"fail":N,"skip":N,"results":[...]}` line — the
proof exists; the ticket gate just doesn't require it.

Source: `.agent/reports/kaizen-qa-loop-2026-06-19.plan.md` (failure classes 1+2) +
`.skeptical-review.md` (P1 findings, all accepted below).

## Scope

- `scripts/agent_tasks/schema.py` — require a `GATES_JSON` proof block in the
  `.dev-summary.md` (for `Dev Complete`) **and** the `.qa.md` (for `Review`).
- `scripts/agent_tasks/constants.py` — the marker + a **lenient** regex (extract
  `"fail":N` / `"skip":N` by field, resilient to key reordering/additions).
- Rule-fires tests + a gates.sh↔parser coupling test; `docs/guides/qa-checkpoints.md`.

## Non-Goals

- **No claim of forgery-proofing.** The `GATES_JSON` is self-pasted, hence forgeable;
  this is an **observability + friction ratchet** whose ultimate authority is CI
  re-running every gate on the same commit (a forged PASS surfaces as CI red). Framed
  honestly per the cold-critic — not "security theater" dressed as a hard control.
- No requiring developers to run Postgres locally (see the SKIP handling in AC).

## Acceptance Criteria

- [ ] `Dev Complete` requires the `.dev-summary.md` to embed a `GATES_JSON` line; `Review`
      requires it in the `.qa.md` (or a wave report it references — see below). **Missing
      block ⇒ validation FAILS.**
- [ ] **`fail>0` ⇒ validation FAILS.** **`skip>0` ⇒ a WARNING, not a block** — CI
      (`GATES_REQUIRE_ALL=1`) is the authority on skips, so blocking on local SKIPs (no
      Postgres ⇒ test/diff-cover/migrations SKIP) would create false positives and push
      agents to lie or skip QA entirely. (Critic P1.2.)
- [ ] The `GATES_JSON` is pinned to the reviewed commit SHA (recorded in the report);
      mismatch with the ticket's branch HEAD ⇒ WARNING.
- [ ] **Lenient parser:** extract `fail`/`skip` via field-regex on the raw line, not a
      full-object re-parse, so a future `gates.sh` JSON change (added/reordered keys)
      doesn't silently break it. (Critic P1.3.)
- [ ] **Coupling test:** a test runs/feeds a real `gates.sh` `GATES_JSON` line and asserts
      the validator parser accepts a genuine PASS line and the rule-fires test rejects a
      no-block / `fail>0` report. (AE-0180 rule-fires standard + the coupling guard.)
- [ ] **Wave reports:** a per-ticket `.qa.md` MAY satisfy the proof by referencing a wave
      report (e.g. `wave-*.qa.md`) that carries the `GATES_JSON`; the validator follows the
      reference. (Critic missing-evidence #5.)

## Gherkin Scenarios

```gherkin
Feature: ticket transitions require machine-readable gate proof

  Scenario: a dev-summary without GATES_JSON cannot reach Dev Complete
    Given a ticket whose .dev-summary.md has no GATES_JSON line
    When validate_ticket runs for the Dev Complete transition
    Then it exits non-zero and names the missing gate proof

  Scenario: a QA report claiming fail>0 cannot reach Review
    Given a .qa.md whose GATES_JSON shows "fail":2
    When validate_ticket runs for the Review transition
    Then it exits non-zero

  Scenario: a clean run with skipped DB gates is allowed with a warning
    Given a .qa.md whose GATES_JSON shows "fail":0 and "skip":3
    When validate_ticket runs
    Then it passes with a warning that CI will decide the skipped gates
```

## Affected Areas

- Backend: scripts/agent_tasks/schema.py, constants.py
- Tests: rule-fires + gates.sh↔parser coupling test
- Docs: docs/guides/qa-checkpoints.md

## Dependencies

- Blocks: AE-0260 (its declared `mode` field extends this evidence block)
- Related: AE-0181 (the existence/attribution gate this strengthens); kaizen-qa-loop-2026-06-19

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested (no block / fail>0 / skip>0 / wave-reference / malformed JSON)
- [ ] Orphan/unfinished code checked

## Decision Log

### 2026-06-19 — external cold-critic findings (accepted)
- BLOCKER P1.1 "forged GATES_JSON undetectable; CI-backstop weaker than claimed" —
  accepted; reframed as an observability+friction ratchet (Non-Goals), authority = CI
  re-run. (A validator that itself re-runs gates was considered but rejected: the
  ticket-hygiene CI job has no Postgres/full env; CI's own gate jobs are the re-run.)
- WARN P1.2 "skip=0 forces false positives" — accepted; `skip>0` is a WARNING, only
  `fail>0`/missing blocks.
- INFO P1.3 "format coupling" — accepted; lenient field-regex + coupling test.
- Missing-evidence #2 "Dev Complete hole" — accepted; the proof now also gates Dev
  Complete via the dev-summary (the actual incident point), not just Review.
- Missing-evidence #5 "wave mode" — accepted; per-ticket `.qa.md` may reference a wave report.

## Test Evidence

`backend/tests/unit/agent_tasks/test_gate_proof.py` (rule-fires, all pass):
`test_dev_complete_blocked_without_gates_json` (a dev-summary saying "All green, trust me."
is BLOCKED), `test_proof_rejects_fail_gt_zero`, `test_proof_warns_on_skip_but_does_not_block`
(skip>0 → warn, not block), `test_real_gates_sh_line_parses` (coupling — runs the real
`gates.sh`), `test_wave_report_reference_satisfies_proof`. Backward-compat:
`validate_all_tickets.py` → **All 255 ticket(s) OK** (enforcement in `can_transition(enforce
_gate_proof=True)` only, not the retroactive sweep). Full gates `PASS=19/FAIL=0/SKIP=0`.

## Blockers

None.

## Final Summary

Pending.
