# AE-0255 — stage external_agent.sh output+sidecar to /tmp so tracked-dir output cannot trip the ae-0170 guard

Status: Intake
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

Make `scripts/lib/external_agent.sh` produce its output and sidecar without mutating the
primary working tree, so an external run whose output path is inside a tracked dir (e.g.
`.agent/reports/`) no longer false-trips the AE-0170 worktree guard — removing the manual
"write output to /tmp" workaround operators currently must remember.

## Problem

`ext_run_guarded` captures `git status --porcelain` on the primary repo before the run and
fails (return 4) if it differs afterward (`external_agent.sh:147`). Two leak sources mutate
that status when output lands in a tracked dir:
1. The `.wt.log` sidecar is written adjacent to the output (`external_agent.sh:119`).
2. The **output file itself** is written to the caller's path; if tracked, it mutates the
   primary tree independently of the sidecar (critic-confirmed).

Both recurred across two sessions (kaizen-session-2026-06-19 landmines). Moving only the
sidecar is a partial fix — the output-file leak persists.

Source: `.agent/reports/kaizen-session-2026-06-19.plan.md` (failure class #2) +
`.skeptical-review.md` (P2 WARN #1 + #2, both accepted).

## Scope

- `scripts/lib/external_agent.sh` — `ext_run_guarded`: stage output + `.wt.log` to a
  `mktemp` location, run, guard-check, then copy the output to the requested path; clean up
  the staged temp files on exit.

## Non-Goals

- No change to the guard's strictness (HOLD — this loosens nothing; the guard keeps full
  strength, only the runner stops mutating the primary tree during the run). Explicit "no
  user-visible behavior change; CI/tooling" classification per CLAUDE.md AE-0153.

## Acceptance Criteria

- [ ] **Guard contract is explicit:** the run executes with the tool's output staged OUTSIDE
      the tracked tree (`mktemp`); the guard check verifies the primary tree is unchanged
      **except** for the single requested output path, which is treated as an *approved,
      intentional* mutation (not a violation). Any OTHER change still fails (return 4). This
      avoids both the false-trip and the TOCTOU gap the reviewer flagged (copy-after-guard
      that the guard never sees).
- [ ] An `ext_run_guarded` invocation whose requested output path is **under a tracked dir**
      returns 0 (not 4), produces the output at that path, and a same-process re-run does NOT
      see the prior output as a spurious `status_before` change (loop-safe). Test asserts both.
- [ ] An `ext_run_guarded` invocation that mutates a tracked file **other than** the output
      path still fails (return 4) — the guard's strictness is preserved (no loosening).
- [ ] The `.wt.log` and the staged output temp are written outside the tracked tree and
      cleaned via a `trap` on all exit paths; the copy/move step has **explicit error handling**
      (cross-filesystem `mv`→`cp` fallback, fail loudly if the output does not land — no silent loss).
- [ ] Existing callers (`run_external_qa.sh`, `run_external_kaizen.sh`) still pass their smoke paths.

## Gherkin Scenarios

```gherkin
Feature: external runner does not trip the AE-0170 guard for tracked-dir output

  Scenario: output requested under .agent/reports leaves the tree clean
    Given ext_run_guarded is called with output ".agent/reports/x.out"
    When the external tool finishes
    Then git status --porcelain on the primary repo is unchanged
      And ".agent/reports/x.out" exists with the tool output
      And no .wt.log remains in the tracked tree
```

## Affected Areas

- Tests: scripts/lib external_agent guard test
- Docs: update the kaizen/QA landmine note (workaround no longer required)

## Dependencies

- Blocks: —
- Blocked by: —
- Related: AE-0170 (the guard); kaizen-session-2026-06-19

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested (tracked-dir output, error path cleanup)
- [ ] Orphan/unfinished code checked

## Decision Log

### 2026-06-19 — external cold-critic findings (plan-round, accepted)
- WARN "output-file leak persists" — accepted; verified `external_agent.sh:147` compares
  primary status; AC now requires staging the output file, not just the sidecar.
- WARN "no cleanup trap" — accepted; AC requires a trap on all exit paths.

### 2026-06-19 — external architect review of the ticket (round 2, accepted)
- WARN "copy-after-guard TOCTOU / loop-unsafe" — accepted; AC reframed so the guard treats
  the single output path as an approved mutation and verifies everything else is unchanged,
  with a loop-safe (re-run) assertion.
- INFO "cross-filesystem mv/cp failure → silent output loss" — accepted; AC requires explicit
  copy error handling.

## Blockers

None.

## Final Summary

Pending.
