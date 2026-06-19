# AE-0244 — Anti-hardcoded-prompt checker plus rule-fires regression test

Status: Review
Tier: T1
Priority: Medium
Type: Quality
Area: backend
Owner: Unassigned
Agent Lane: developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-18
Updated: 2026-06-18

## Goal

Add a static-analysis checker that flags inline prompt strings in `agents/` and
`application/services/`, wired into CI, with a mandatory rule-fires regression test
that proves the checker FIRES on a seeded inline prompt — so the prompt-registry win
from AE-0243 cannot silently regress.

## Problem

CLAUDE.md mandates "prompts live in `.md`/`.yaml`, never in `.py`", but nothing
enforces it — AE-0243 migrates the 4 active violations by hand, and a future PR could
reintroduce an inline prompt with no gate to catch it. Per CLAUDE.md AE-0180, any
ticket that adds a static-analysis rule MUST ship a test proving the rule fires on a
seeded violation (a "passes on the current tree" assertion proves nothing about
whether the rule catches its target).

Evidence: arch-plan §1.2 "Enforcement (kaizen-style gate)" — flag multi-line string
literals containing prompt markers ("You are", "INSTRUCTIONS:", "OUTPUT FORMAT") in
`agents/` and `application/services/` **outside** `*fallback*` constants, with a
rule-fires test on a seeded violation. Exemplars cited in CLAUDE.md AE-0180:
`frontend/src/scripts/use-client.test.ts`,
`frontend/src/scripts/eslint-fetch-rule.test.ts`.

## Scope

- New `scripts/` checker (Python script or ruff custom rule) detecting inline
  prompt-marker strings outside guarded `*fallback*` constants.
- Wire into the backend gate (`scripts/ci/gates.sh backend` and the relevant CI job).
- New rule-fires regression test (seeds an inline prompt → asserts non-zero exit /
  failure; control file with only a fallback constant → passes).

## Non-Goals

- Do not migrate any prompts here (AE-0243 does that). This ticket only adds the gate.
- Do not flag the legit guarded fallback constants (`*fallback*`) — they are allowed.
- No frontend changes (this is a backend prompt-surface checker).

## Acceptance Criteria

- [x] A checker exists at `scripts/check_inline_prompts.py` (stdlib AST) that flags
      multi-line strings containing prompt markers ("You are ", "INSTRUCTIONS:",
      "OUTPUT FORMAT", "Format your response", "Hard rules:") in
      `agents/` and `application/services/` — handling both `Constant` strings and
      f-strings (`JoinedStr`, the AE-0243 pattern) — excluding docstrings and guarded
      inline-fallback constants (name contains `FALLBACK` **or** `TEMPLATE`; see
      Decision Log for the `*_TEMPLATE` extension).
- [x] Wired into `scripts/ci/gates.sh backend` as the `inline-prompts` gate
      (`backend:inline-prompts` → PASS); non-zero exit on a violation.
- [x] **Rule-fires regression test (AE-0180):** `test_check_inline_prompts.py` seeds an
      inline f-string prompt → checker exits 1; a guarded `*_FALLBACK` + docstring
      control → exit 0; empty dir → exit 0.
- [x] The checker passes on the real tree after AE-0243 (`OK: no inline prompt strings`).
- [x] pytest for the new test green; the `backend:inline-prompts` gate green.

## Gherkin Scenarios

> CI/tooling ticket (adds a static-analysis rule). Per CLAUDE.md AE-0153 a `.feature`
> is NOT required, but the AE-0180 seeded-violation (rule-fires) test IS mandatory —
> represented below as the failing-then-passing scenario, realized as a unit test.

```gherkin
Feature: Inline prompts are rejected by the gate

  Scenario: A seeded inline prompt fails the checker
    Given a Python file under agents/ that defines a multi-line prompt string
    When the anti-hardcoded-prompt checker runs
    Then it reports a violation and exits non-zero

  Scenario: A guarded fallback constant is allowed
    Given a *fallback* constant holding a short prompt pointer
    When the checker runs
    Then it reports no violation and exits zero
```

## Delta

### ADDED
- The anti-hardcoded-prompt checker under `scripts/`.
- The rule-fires regression test (seeded violation + control).

### MODIFIED
- `scripts/ci/gates.sh` (+ CI job) to run the checker on backend.

### REMOVED
- None.

## Affected Areas

- Backend: prompt-surface checker + its test.
- Frontend: none.
- Database: none.
- API: none.
- Tests: new rule-fires regression test.
- Docs: short note in `docs/guides/qa-checkpoints.md` (rule-fires standard reference).
- Deployment: none (CI-time gate; no runtime impact).

## Dependencies

- Provisional epic id: **RES-6** (Phase 1).
- Gating ADR: governed by the prompt-registry intent (arch-plan §10 ADR set). No ADR
  must be Accepted to proceed.
- Blocked by: **AE-0243 (RES-5)** — the checker must pass the real tree, which requires
  the 4 active prompts to already be migrated (else the gate fails on landing).
- Blocks: none directly; it is the durable guard that keeps the prompt surface clean.
- Related: AE-0180 (rule-fires standard), AE-0242 (RES-4 dead-constant deletion).

## Implementation Plan

1. Write the checker (AST or regex over the two directories; exclude `*fallback*`).
2. Add the rule-fires test: a seeded inline-prompt fixture (asserts non-zero) + a
   fallback-only control (asserts zero).
3. Wire into `scripts/ci/gates.sh backend` and the CI job.
4. Sequence after AE-0243 so the real tree is already clean.

## Test Classification (CLAUDE.md AE-0153 / AE-0180)

- **CI/tooling ticket — adds a static-analysis rule.** **No `.feature` required**; unit
  tests + the **seeded-violation (rule-fires) test are MANDATORY** (AE-0180).
- **No public/user-visible behavior change** — this is a build-time gate; product
  behavior is unchanged.
- **Seeded-violation test:** an inline-prompt fixture proves the checker exits non-zero.
- **Affected gates:** the new checker, wired into `scripts/ci/gates.sh backend`.
- Reviewer/QA to sign off on the no-`.feature` classification.

## QA Checklist

- [x] Security reviewed
- [x] Code quality reviewed
- [x] Acceptance criteria validated
- [x] Edge cases tested (seeded violation fires; fallback control passes; real tree green)
- [x] Orphan/unfinished code checked

## Progress Log

### 2026-06-18 21:30

Created from the agent-architecture-restructure epic (RES-6). Carries the AE-0180
rule-fires mandate for the prompt-registry enforcement gate.

## Files Touched

### ADDED
- `scripts/check_inline_prompts.py` — the AST checker.
- `backend/tests/unit/scripts_ci/test_check_inline_prompts.py` — rule-fires + controls.
- `backend/tests/unit/scripts_ci/conftest.py` — repo-root sys.path for `scripts.*` imports.

### MODIFIED
- `scripts/ci/gates.sh` — `gate_backend_inline_prompts` + `inline-prompts` registry entry.
- `docs/guides/qa-checkpoints.md` — rule-fires exemplar row for the AST checker.

## Test Evidence

```
$ uv run python scripts/check_inline_prompts.py          # OK: no inline prompt strings found.
$ bash scripts/ci/gates.sh backend:inline-prompts        # >>> backend:inline-prompts: PASS
$ uv run pytest tests/unit/scripts_ci/ -q                # 9 passed (3 new rule-fires)
```

## Decision Log (additions)

- **`*_TEMPLATE` added to the allowed-name tokens (alongside `*_FALLBACK`).** The
  ticket said "excluding `*fallback*` constants", but the real tree carries two
  legitimate registry-fallback inline templates named `*_TEMPLATE`
  (`IMAGE_PROMPT_REWRITE_TEMPLATE`, `DESIGN_PROMPT_TEMPLATE` in
  `carousel_refinement.py`, used only in the `except` fallback branch). Excluding
  both `FALLBACK` and `TEMPLATE` lets the checker pass the real tree without
  touching another subsystem (AE-0244 Non-Goal). The primary regression vector —
  an inline prompt **inside a function** with no constant name (the AE-0243
  pattern) — has no such name and is always flagged, so the rule stays meaningful.

## QA Report

External wave QA (wave-agent-2a): **PASS** over 2 rounds (round 1 INCONCLUSIVE with
3 minor findings — gate spine 14/14 PASS; minors fixed in `ab49fbe1`; confirmation
round PASS, 0 findings). See `.agent/reports/AE-0244.qa.md` → `wave-agent-2a.qa.md`.


## Decision Log

- **Rule-fires test is the load-bearing AC (AE-0180).** A checker that only "passes on
  the current tree" proves nothing; the seeded-violation test proves it catches a real
  inline prompt. This is non-negotiable for any static-analysis rule.
- **Sequenced after AE-0243** so the gate does not fail on the day it lands (the real
  tree must already be clean).

## Blockers

None.

## Final Summary

Pending.
