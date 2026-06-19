# AE-0259 — ship gate-capture wrapper and codify full-gate loop discipline (no pipe-masked exits)

Status: In Development
Tier: T1
Priority: High
Type: Quality
Area: Cross-cutting
Owner: Unassigned
Agent Lane: developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-19
Updated: 2026-06-19

## Goal

Make the correct way to run gates the **only easy way**: a wrapper that runs the full
gate set, captures the real exit code + the `GATES_JSON` verdict to a deterministic
file, and cannot be defeated by piping. Plus codify the loop discipline that was only
ever an agent memory.

## Problem

Two sub-failures this session: (1) `bash scripts/ci/gates.sh <scope> | tail -n45`
returned the **pipe's** exit (tail = 0), masking a non-zero gate — a PR was misread as
green while 3 tests actually failed. (2) The "run the full gate set before Dev Complete"
expectation lived only in an agent memory, not a project rule, so the loop ran a subset
and trusted a subagent's self-report.

Source: `.agent/reports/kaizen-qa-loop-2026-06-19.plan.md` (failure class 3 + the
written-rule gap) + `.skeptical-review.md` (P2.1/P2.2 accepted — upgraded from doc-only
to a real wrapper).

## Scope

- `scripts/ci/gate-capture.sh <scope>` — runs `gates.sh <scope>`, writes stdout+stderr
  to a deterministic log (e.g. `.agent/reports/.gates-capture-<scope>.log`), captures and
  **prints the gate's real exit code**, and echoes the `GATES_JSON` line. It writes, it
  does not pipe — so the exit cannot be masked. Bridges AE-0258 (deterministic GATES_JSON capture).
- `CLAUDE.md` + `docs/guides/qa-checkpoints.md` — the loop-discipline rule.

## Non-Goals

- No change to `gates.sh` gate definitions/thresholds. (This is CI/tooling; explicit "no
  user-visible behavior change" per CLAUDE.md AE-0153.)
- Do NOT forbid `gates.sh --changed-only` during iteration (see AC).

## Acceptance Criteria

- [ ] `scripts/ci/gate-capture.sh <scope>` exists, runs the **full** gate set, writes the
      capture log, and exits with the **gate's** exit code (a seeded failing gate ⇒ the
      wrapper exits non-zero — proven by a test, NOT defeatable by a trailing pipe).
- [ ] CLAUDE.md states: the delivery loop runs the **full** `gates.sh <scope>` (via
      `gate-capture.sh`) + `check-integrity.sh` + `/qa-agent` before **Dev Complete**;
      never declare green on a gate subset, a delegated agent's self-report, or by
      deferring to CI; **never pipe a gate to `tail`/`head`** (the pipe's exit masks the
      gate's — capture the exit to a file instead).
- [ ] **Precise on `--changed-only`** (critic P2.2): `--changed-only` is fine for fast
      iteration; the **Dev Complete declaration** must be based on a **full** gate run.
- [ ] A rule-fires test: a stubbed failing gate makes `gate-capture.sh` exit non-zero and
      writes the capture log.

## Gherkin Scenarios

```gherkin
Feature: gate runs cannot be pipe-masked

  Scenario: the wrapper surfaces a failing gate's real exit code
    Given a gate that fails
    When gate-capture.sh runs that scope
    Then it exits non-zero and writes the capture log with the GATES_JSON line
```

## Affected Areas

- Backend: scripts/ci/gate-capture.sh
- Tests: wrapper exit-code rule-fires test
- Docs: CLAUDE.md, docs/guides/qa-checkpoints.md

## Dependencies

- Related: AE-0258 (consumes the deterministic GATES_JSON capture); kaizen-qa-loop-2026-06-19

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested (failing gate, --changed-only note)
- [ ] Orphan/unfinished code checked

## Decision Log

### 2026-06-19 — external cold-critic findings (accepted)
- WARN P2.1 "purely documentary; ship a wrapper instead" — accepted; upgraded from a
  doc-only rule to a real `gate-capture.sh` wrapper that makes pipe-masking structurally
  impossible and bridges AE-0258.
- INFO P2.2 "'no subset' conflicts with --changed-only fast loop" — accepted; the rule
  permits `--changed-only` for iteration and requires a full run only at the Dev Complete
  declaration.

## Blockers

None.

## Final Summary

Pending.
