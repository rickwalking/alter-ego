# AE-0260 — require external qa by default for agent-authored work with declared mode field

Status: In Development
Tier: T1
Priority: Medium
Type: Quality
Area: Cross-cutting
Owner: Unassigned
Agent Lane: developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-19
Updated: 2026-06-19

## Goal

Make bias-free (external) QA the **default** for agent-authored work — so it does not
depend on a human asking — and make the QA mode an explicit, declared field in the
evidence block.

## Problem

The qa-agent skill **lists** an external QA mode "when the implementation was authored
in the same session" (SKILL.md:104) but does not **require** it, so same-session /
subagent-authored code is self-reviewed by default; this session, external QA ran only
after the operator demanded it. Self-review grades its own work leniently (same rationale
as the architect cold-critic).

Source: `.agent/reports/kaizen-qa-loop-2026-06-19.plan.md` (failure class 4) +
`.skeptical-review.md` (P3 — the "validator detects same-session" mechanism was **rejected
as unenforceable** and is replaced below).

## Scope

- `skills/delivery/qa-agent/SKILL.md` + `config.yaml` — **default to external** QA for
  agent/same-session-authored work (a process ratchet; mirrors AE-0257's required-skeptical-for-T3).
- The `.qa.md` evidence block (AE-0258) gains a **declared `mode:` field**
  (`external` | `self` | `self-fallback`); `validate_ticket` checks the field is present
  and is an allowed value.

## Non-Goals

- **The validator does NOT (cannot) detect "same session" from file content** (critic
  P3.1 — there is no session identity in any markdown file). Enforcement is the SKILL.md
  default + a mechanical declared-`mode` check; truthfulness of `mode: self` is policed by
  the human reviewer, not the validator. No false claim that the validator verifies session identity.

## Acceptance Criteria

- [ ] `qa-agent` SKILL.md + config.yaml state external QA is the **default/required** mode
      for agent-authored or same-session work (not discretionary).
- [ ] The `.qa.md` evidence block carries a `mode:` field; `validate_ticket` FAILS a
      `Review` transition whose report omits `mode:` or uses a non-allowed value. (Mechanical,
      implementable — unlike session detection.)
- [ ] **Fallback** (critic missing-evidence #4): when the external toolchain
      (`run_external_qa.sh`: opencode → codex → cursor) is unavailable, `mode: self-fallback`
      is allowed **with a stated reason**; the SKILL documents this path so a tool outage is
      not a hard block.
- [ ] **Wave compatibility:** a wave `.qa.md` (one external run over N tickets) satisfies
      the `mode: external` requirement for each referenced ticket.
- [ ] A rule-fires test: a `.qa.md` with no `mode:` (or an invalid value) fails validation.

## Gherkin Scenarios

```gherkin
Feature: agent-authored work defaults to external QA with a declared mode

  Scenario: a QA report without a declared mode cannot reach Review
    Given a .qa.md with no mode: field
    When validate_ticket runs for the Review transition
    Then it exits non-zero

  Scenario: external toolchain down is handled, not blocked
    Given the external QA tools are unavailable
    When QA runs and records mode: self-fallback with a reason
    Then validate_ticket accepts it
```

## Affected Areas

- Docs: skills/delivery/qa-agent/SKILL.md, config.yaml
- Backend: scripts/agent_tasks/schema.py (declared-mode check)
- Tests: rule-fires test for the mode field

## Dependencies

- Blocked by: AE-0258 (the `mode:` field extends AE-0258's evidence block) — per critic P3.2
- Related: AE-0257 (required-external-skeptical-for-T3 — same pattern); kaizen-qa-loop-2026-06-19

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested (missing mode / self-fallback / wave)
- [ ] Orphan/unfinished code checked

## Decision Log

### 2026-06-19 — external cold-critic findings (accepted)
- BLOCKER P3.1 "'same session' is undetectable by a static validator" — **accepted**;
  dropped the detect-and-enforce mechanism. Enforcement is now: SKILL.md default-to-external
  + a mechanical declared-`mode` field check; truthfulness policed by the human reviewer.
- WARN P3.2 "P3 depends on P1" — accepted; sequenced after AE-0258, the `mode:` field
  extends AE-0258's evidence block.
- Missing-evidence #4 "external toolchain unavailable" — accepted; `mode: self-fallback`
  with a reason is an allowed path.

## Blockers

None.

## Final Summary

Pending.
