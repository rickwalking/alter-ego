# AE-0239 — gates.sh preflight: distinguish missing tool from real violation (SKIP not FAIL)

Status: Dev Complete
Tier: T1
Priority: Medium
Type: Quality
Area: Cross-cutting
Owner: Unassigned
Branch: TBD
Created: 2026-06-18
Updated: 2026-06-18

## Goal

When a frontend gate's underlying tool (`jscpd`, `knip`) is not installed locally,
`scripts/ci/gates.sh` must report an honest **SKIP** with an actionable message —
never a cryptic exit-127 **FAIL** that reads like a real violation.

## Problem

Failure class **FC-3** (kaizen session-2026-06-18c). Frontend gates shell out to
`jscpd`/`knip`. When those binaries are absent locally they exit **127**, and
`run_gate` maps any unrecognised exit to **FAIL** (`gates.sh` `*) status="FAIL"`), so
a clean tree reads as broken. This recurs (it cost time again this session) and risks
masking a *real* failure as "just env". CI installs the tools via `npm ci`, so CI is
unaffected — this is purely local-signal fidelity.

Reports: `.agent/reports/kaizen-session-2026-06-18c.{signal,plan,skeptical-review}.md`.

## Scope

- `scripts/ci/gates.sh` — a preflight for tool-dependent frontend gates.

## Non-Goals

- Do **not** make a missing tool PASS. SKIP is inconclusive, never PASS
  (`GATES_REQUIRE_ALL=1` in CI still turns SKIP into FAIL — correct, because CI must
  have the tool).
- No change to the actual duplication/dead-file thresholds.

## Acceptance Criteria

- [x] A preflight resolves each required tool via **`node_modules/.bin/<tool>`** (not
      `which`/`command -v`; not `npx`). Done: `scripts/lib/require_tool.sh::require_tool`
      probes `$FRONTEND_BIN_DIR/<tool>` (`-x`).
- [x] When the tool is missing, the gate returns **`EXIT_SKIP` (77)** with the message
      `devDependency '<tool>' not installed — run \`cd frontend && npm ci\``, so
      `run_gate` reports **SKIP** locally (and **FAIL** under `GATES_REQUIRE_ALL=1` in
      CI). Proven by the integration test (both modes).
- [x] The advisory gates (`gate_frontend_dead_files`, `gate_frontend_duplication_tests`)
      keep their advisory semantics — a missing tool yields SKIP (preflight returns
      before the `|| echo ADVISORY` swallow), not a swallowed false PASS.
- [x] **Seeded-violation proof:** `test_require_tool.py` hides the binary (empty
      `FRONTEND_BIN_DIR`) and asserts SKIP(77) + the actionable message — the preflight
      fires. Also asserts the real `gates.sh frontend:dead-files` reports SKIP.
- [x] With tools present, the preflight returns 0 and the gate runs as today
      (`test_require_tool_passes_when_binary_present`).

## Gherkin Scenarios

```gherkin
Feature: gates.sh tells "tool missing" apart from "real violation"

  Scenario: knip is not installed locally
    Given node_modules/.bin/knip is absent
    When the dead-files gate runs
    Then it exits 77 (SKIP) with a "run npm ci" message
    And it does not report PASS or a raw FAIL

  Scenario: jscpd is installed
    Given node_modules/.bin/jscpd exists
    When the duplication gate runs
    Then it runs jscpd and reports the real result
```

## Delta

### ADDED
- A `_require_tool <name>` preflight helper in `gates.sh`.
- A seeded missing-tool test.

### MODIFIED
- Tool-dependent frontend gate functions call the preflight first.

### REMOVED
- None.

## Affected Areas

- Backend: none.
- Frontend: none (build/runtime unchanged).
- Tests: a shell/unit test for the preflight.
- Deployment: none.
- Docs: optional one-liner in the gate docs.

## Dependencies

- Blocks: cleaner local QA runs; fewer false "frontend gate failing" reports.
- Blocked by: none.
- Related: AE-0178 (knip advisory dead-files), the `.jscpd.json` threshold gate.

## Implementation Plan

1. Add `_require_tool` that checks `frontend/node_modules/.bin/<tool>`; on miss, echo
   the actionable message and `return "$EXIT_SKIP"`.
2. Call it at the top of each tool-dependent gate.
3. Add the seeded test (hide the binary → assert exit 77 + message).

## Test Classification (CLAUDE.md AE-0153 / AE-0180)

- **CI/tooling ticket.** **Unit/shell test + the seeded missing-tool test suffice; no
  `.feature` required.**
- **No public/user-visible behavior change** — gate signal fidelity only.
- **Seeded-violation test:** binary hidden → preflight returns SKIP(77) + message.
- **Affected gates:** local `gates.sh frontend` (duplication, dead-files).
- Reviewer/QA to sign off on the no-`.feature` classification.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested (tool present / absent; advisory vs blocking gate)
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-18 21:00

Created by kaizen session-2026-06-18c (FC-3). Cold-critic (opencode) sharpened the
design: return EXIT_SKIP(77) not FAIL, and probe `node_modules/.bin/<tool>` rather
than `which`/`npx` (verified against `gates.sh`: `EXIT_SKIP=77`, unknown exits→FAIL).

## Files Touched

- `scripts/lib/require_tool.sh` (NEW) — sourceable `require_tool <tool>` preflight
  (probes `$FRONTEND_BIN_DIR/<tool>`; SKIP 77 + actionable message on miss).
- `scripts/ci/gates.sh` — sources the lib; `gate_frontend_{duplication,dead_code,
  duplication_tests,dead_files}` call `require_tool <jscpd|knip> || return $?`.
- `backend/tests/unit/scripts_ci/test_require_tool.py` (NEW) — seeded missing-tool
  (SKIP 77 + message), tool-present (0), and `gates.sh` integration (SKIP locally,
  FAIL under `GATES_REQUIRE_ALL=1`).

Followed the existing sourceable-lib pattern (`scripts/lib/diff_base.sh` +
`test_diff_base.py`) so both preflight branches are unit-testable without `npm`.

## Test Evidence

```
$ uv run pytest tests/unit/scripts_ci/test_require_tool.py -q
3 passed in 0.11s
$ bash -n scripts/ci/gates.sh scripts/lib/require_tool.sh   # syntax OK
```

## QA Report

Pending.

## Decision Log

- **Critic [WARN] preflight must SKIP, not FAIL, on advisory gates** — ACCEPTED:
  return `EXIT_SKIP` (77). Confirmed in `gates.sh` that 77→SKIP locally and →FAIL under
  `GATES_REQUIRE_ALL=1` (CI), which is the correct behavior (CI must have the tool).
- **Critic [WARN] use node_modules/.bin, not `which`/`npx`** — ACCEPTED: `which` misses
  npm-local binaries and `npx` would auto-install and mask the missing-tool case;
  probe `frontend/node_modules/.bin/<tool>` directly.

## Blockers

None.

## Final Summary

Pending.
