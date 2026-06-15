# AE-0078 — Record import-violation and public-contract baseline

Status: Review
Tier: T2
Priority: Medium
Type: Research
Area: Backend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: docs/ae-0078-import-baseline
Kanban Card: TBD
Created: 2026-06-12
Updated: 2026-06-12

## Goal

A committed baseline of every current architecture violation that the
Import Linter wildcards hide, plus the de-facto public contracts between
layers, so Phase 1 ratchets start from measured numbers.

## Problem

`backend/.importlinter` ignores `application.** -> infrastructure.**` and
`application.** -> agents.**`, so CI passes while the violations it should
catch are unmeasured. Phase 1 replaces wildcards with an exact generated
baseline; Phase 0 must first record what that baseline is. Two scoped
categories (`api -> infrastructure`, `agents -> application`) are not
wildcard-hidden — the first is currently allowed by contract 4 and the
second has no Import Linter contract at all — but both are forbidden in
the target architecture, so the baseline measures them too (by script,
not lint-imports).

## Scope

- Generate the full violation list for: application→infrastructure,
  application→agents, agents→application, api→infrastructure,
  `get_container()` calls outside bootstrap-eligible code, and
  `.commit()` calls inside repository adapters.
- Record per-category counts and the exact importing file/line list in
  `.agent/reports/import-violations-baseline.md`.
- Record the de-facto public contracts: which symbols each layer imports
  from another layer's modules (top 20 by frequency per category).
- No CI or `.importlinter` changes — measurement only.

## Non-Goals

- No `.importlinter` edits, no ratchets, no violation fixes (Phase 1).
- No frontend boundary analysis (AE-0077 covers frontend measurement;
  boundary rules are Phase 1/7).

## Acceptance Criteria

- [x] `.agent/reports/import-violations-baseline.md` exists with one
      section per category listed in Scope
- [x] Every section has a total count and a file-level listing generated
      by a copy-pasteable command (lint-imports debug output, `rg`, or a
      small script — command included in the report)
- [x] `get_container()` call sites outside `api/app.py` and
      `api/dependencies/` are individually listed
- [x] Repository adapters that call `.commit()` internally are
      individually listed
- [x] Running the documented commands twice yields identical results
- [x] The report distinguishes wildcard-hidden violations
      (application→infrastructure, application→agents) from
      currently-allowed-but-target-forbidden imports (api→infrastructure,
      agents→application)
- [x] WHEN Phase 1 later replaces the wildcard ignores THE baseline file
      SHALL be usable as the initial exception list (machine-readable
      appendix: one `module -> module` pair per line)
- [x] CI behavior is unchanged (`git diff` shows no workflow or
      `.importlinter` modifications)

## Gherkin Scenarios

Not applicable — measurement and documentation only; no runtime behavior.

## Delta

### ADDED

- `.agent/reports/import-violations-baseline.md`
- Optional helper script under `scripts/` if commands exceed a few lines

### MODIFIED

- None

### REMOVED

- None

## Affected Areas

- Backend: analyzed, not changed
- Frontend: none
- Database: none
- API: none
- Tests: none
- Docs: baseline report
- Prompts/LLM: none
- Observability: none
- Deployment: none

## Dependencies

- Blocks: Phase 1 Import Linter ratchet tickets
- Blocked by: none
- Related: AE-0070; this baseline feeds AE-0072's evidence appendix

## Implementation Plan

1. Run Import Linter with wildcards temporarily disabled in a scratch
   config to enumerate violations (no committed config change).
2. `rg` sweeps for `get_container(` and repository `.commit()` patterns.
3. Write the report with the machine-readable appendix.

## QA Checklist

- [x] Security reviewed (fixture/report audit; PASS 100/100)
- [x] Code quality reviewed (ruff clean; scripts robust)
- [x] Acceptance criteria validated (all verified independently)
- [x] Edge cases tested (reproducibility, scanner blind spots)
- [x] Orphan/unfinished code checked (all artifacts accounted for)

## Progress Log

### 2026-06-12 00:00

Ticket created by planner.

### 2026-06-12 (development)

Implemented on docs/ae-0078-import-baseline via committed stdlib
scanner (regex import scan, same signal as lint-imports sans wildcards).

## Files Touched

- `scripts/metrics/import_baseline.py` (new generator, stdlib-only)
- `.agent/reports/import-violations-baseline.md` (new report)
- No `.importlinter`, workflow, or production-code changes (verified:
  `git diff --stat -- backend/.importlinter .github/` is empty)

## Test Evidence

```bash
python3 scripts/metrics/import_baseline.py > a
python3 scripts/metrics/import_baseline.py > b
diff -q a b   # byte-identical
```

Counts: application→infrastructure 66 lines / 63 pairs (wildcard-hidden);
application→agents 26 / 23 (wildcard-hidden); agents→application 22 / 22
(no contract today); api→infrastructure 101 / 98 (contract-4-allowed);
get_container() outside api/app.py + api/dependencies/: 26 sites;
.commit() inside infrastructure/database adapters: 9 sites. Violations
grew since the research scan (58→66, 20→26) — ratchet justification.

## QA Report

`.agent/reports/wave1.qa.md` — wave-level external OpenCode QA
(CrofAI/kimi-k2.6): round 1 WARN 90/100 (A-), zero blockers, all ACs for
AE-0078 verified independently; round 2 confirmation after fix commit
716dba5: **PASS**. Status moved to Review per protocol.

## Decision Log

Pending.

## Blockers

None.

## Final Summary

Baseline recorded with a committed deterministic generator; wildcard-
hidden vs target-forbidden categories separated; de-facto public
contracts captured (top-20 imported symbols per category); machine-
readable module-pair appendix ready as Phase 1's initial exception
list. CI untouched.
