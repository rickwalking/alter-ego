# AE-0257 — require external skeptical pass for t3 current-state plans in architect-skill

Status: Intake
Tier: T2
Priority: Medium
Type: Quality
Area: Cross-cutting
Owner: Unassigned
Agent Lane: architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-19
Updated: 2026-06-19

## Goal

Make the cross-LLM external skeptical pass a REQUIRED-and-ENFORCED step for **every T3 plan**
— the mechanism that actually caught the false-assertion incidents — instead of leaving it
conditional ("skeptical if high-risk") and unenforced. Per architect review, a SKILL.md text
change alone changes nothing (the same agent that skipped "if high-risk" can skip "required");
this ticket therefore also adds a **lightweight existence gate** so the requirement is checkable.

## Problem

Architecture planning is done partly by LLM subagents that scan the repo. Twice they
asserted FALSE current-state facts ("skills/runtime is empty", "chat agents are stateless")
by trusting their own scan; only an external cold-critic + manual `file:line` checks caught
them (kaizen-session-2026-06-19; also memory `kaizen-measurement-rigor`). The architect
skill currently routes T3 as `plan → research → validate → skeptical **if high-risk**`
(`architect-skill/SKILL.md:32`) — so the one cross-LLM check that reliably catches these is
optional.

The cold-critic itself flagged (and we accept) that a self-enforced "cite file:line" doc
rule is circular — the agent that fabricated the assertion is the same one asked to verify
it, and it can hallucinate well-formatted-but-wrong cites. So the ratchet is the REQUIRED
cross-LLM pass, not self-citation.

Source: `.agent/reports/kaizen-session-2026-06-19.plan.md` (failure class #4) +
`.skeptical-review.md` (P4 WARN + INFO, accepted).

## Scope

- `skills/delivery/architect-skill/SKILL.md` — change T3 routing (line 32) + the tier table
  so external skeptical is **required** for **every T3 plan** (drop the fuzzy/ungated "if
  high-risk" and the subjective "current-state facts" qualifier — a crisp, testable trigger).
- `skills/delivery/architect-skill/config.yaml` — reflect the same requirement (no drift).
- **Enforcement gate:** a lightweight check (in `scripts/` and/or the ticket validator) that
  fails when a **T3 ticket whose plan artifact exists** (`.agent/reports/AE-####.arch-plan.md`
  or the planning-complete state) has **no** corresponding `.agent/reports/AE-####.skeptical-review.md`.
- Soft, explicitly **non-ratcheting** guidance: encourage `file:line` cites for current-state
  assertions, labeled advisory (does not by itself raise the bar).

## Non-Goals

- No NLP/semantic scan of plan prose for "false assertions" (infeasible); the gate is a
  file-existence check only.
- Do NOT make the self-cite rule the primary enforcement (circular; can induce hallucinated cites).
- T2 plans are **out of scope** here but acknowledged as a residual gap (see Decision Log) —
  follow-up if the failure class recurs on T2.

## Acceptance Criteria

- [ ] `architect-skill/SKILL.md` T3 routing + tier table state external skeptical is
      **required for every T3 plan** (crisp trigger, not "if high-risk").
- [ ] `architect-skill/config.yaml` is consistent with the SKILL.md change (no drift).
- [ ] **Enforcement gate exists and FIRES on a seeded violation (AE-0180):** a T3 ticket with
      a plan artifact but no `*.skeptical-review.md` makes the check exit non-zero; a control
      (review present) exits zero. This is what converts the doc change into a real ratchet.
- [ ] The `file:line`-cite guidance is present and explicitly labeled advisory / non-ratcheting.
- [ ] The skill validator / doc-consistency check passes with the change.

## Gherkin Scenarios

```gherkin
Feature: every T3 plan requires an enforced external skeptical pass

  Scenario: T3 routing lists skeptical as required
    Given an architect T3 plan
    When the architect skill routing is consulted
    Then the external skeptical pass is listed as a required step (not conditional)

  Scenario: the gate fires when a T3 plan has no skeptical review
    Given a T3 ticket with a plan artifact but no AE-####.skeptical-review.md
    When the enforcement check runs
    Then it exits non-zero and names the missing review

  Scenario: the gate passes when the review exists
    Given a T3 ticket with a plan artifact and its AE-####.skeptical-review.md
    When the enforcement check runs
    Then it exits zero
```

## Affected Areas

- Docs: skills/delivery/architect-skill/SKILL.md, config.yaml
- Tests: skill-consistency / validator check if present

## Dependencies

- Blocks: —
- Blocked by: —
- Related: memory `kaizen-measurement-rigor`; kaizen-session-2026-06-19

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested (tier-table/config drift)
- [ ] Orphan/unfinished code checked

## Decision Log

### 2026-06-19 — external cold-critic findings (plan-round, accepted)
- WARN "self-enforced cite rule is circular / may induce hallucinated cites" — accepted;
  the required cross-LLM skeptical pass is the ratchet; self-cite demoted to advisory.
- INFO "T3 routing change touches tier table + config.yaml" — accepted; both in scope.

### 2026-06-19 — external architect review of the ticket (round 2, accepted)
- BLOCKER "purely documentary, zero enforcement — same agent can skip 'required' as it
  skipped 'if high-risk'" — **accepted**; flipped the non-goal, added a lightweight
  existence gate (T3 plan ⇒ skeptical-review artifact) with an AE-0180 rule-fires test.
  Tier bumped T1→T2 and architect added to the lane.
- WARN "'current-state facts' is undefined/unenforceable" — accepted; trigger is now "every
  T3 plan" (crisp), not the subjective qualifier.
- INFO "T2 plans equally vulnerable but uncovered" — accepted; recorded as an explicit
  out-of-scope residual gap with a follow-up condition.

## Blockers

None.

## Final Summary

Pending.
