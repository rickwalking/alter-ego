# AE-0292 — external-agent runner pins funded glm model (opencode-go/glm-5.2)

Status: Review
Tier: T1
Priority: P1
Type: Quality
Area: backend
Owner: Unassigned
Branch: feat/kaizen-wave-ae0322-0328
Created: 2026-07-01
Updated: 2026-07-22

## Goal

The external-agent CLI runner invokes the funded `opencode-go/glm-5.2` model by default so external QA/kaizen/skeptical runs stop resolving opencode's out-of-balance Zen default.

## Problem

`scripts/lib/external_agent.sh:50` runs `opencode run --agent plan "$(cat $prompt_file)"` with **no `-m` flag**, so the model resolves to opencode's default provider (Zen, currently out of balance). Every external QA / kaizen / skeptical orchestration silently hits the wrong provider; the AE-0290/0291 wave had to bypass the runner and call `opencode -m opencode-go/glm-5.2` by hand. Verified by external cold-critic. Recurs across sessions (logged twice in learnings + memory `external-review-opencode-go-route`). Ratchet: HOLD (makes an existing guardrail actually function).

## Scope

- `scripts/lib/external_agent.sh` — add `EXT_OPENCODE_MODEL="${EXT_OPENCODE_MODEL:-opencode-go/glm-5.2}"` and pass `-m "$EXT_OPENCODE_MODEL"` in `_ext_run_opencode`.
- Document the env override in `~/.claude/skills/qa-agent/config.yaml` and `kaizen-skill/config.yaml`.
- Seeded-invocation test asserting the `-m` flag is present.

## Non-Goals

- Do not change the codex / cursor-agent fallback branches beyond model parity.
- Do not hardcode a model that removes the env override.

## Acceptance Criteria

- [x] Default `opencode` invocation in `external_agent.sh` includes `-m opencode-go/glm-5.2`.
- [x] `EXT_OPENCODE_MODEL` env var overrides the default.
- [x] A seeded test asserts the built command contains the `-m` flag (proves the wiring, not just that the tree passes).
- [x] Engagement sanity check (kaizen 2026-07-22, P2): empty/whitespace-only output → one retry with a "do NOT use tools — respond with analysis only" preamble (the 2026-07-18 r2 lesson), then hard-fail with a distinct exit code so the codex/cursor fallback chain engages instead of a silent empty verdict. Seeded test via a fake `opencode` shim returning empty output.
- [x] Funded-route list documented next to the `EXT_OPENCODE_MODEL` env var (runbook notes: stdin `</dev/null`, background + Monitor for 3–8-min reasoning runs).
- [x] `bash scripts/ci/gates.sh` (relevant scope) green.

## Repro Steps

1. ...

## Affected Areas

- [ ] Backend
- [ ] Frontend
- [ ] Tests

## Dependencies

None.

## Progress Log

### 2026-07-22 — development complete (wave feat/kaizen-wave-ae0322-0328)

Implemented: -m $EXT_OPENCODE_MODEL pin (default opencode-go/glm-5.2) in _ext_run_opencode; _ext_opencode_engaged empty-output retry with no-tools preamble then exit 5 (EXT_EXIT_EMPTY_OUTPUT); funded-route list documented in the lib header + both skill configs. Commit 8e44f30a.

### 2026-07-01 HH:mm

Ticket created.

### 2026-07-22

Kaizen session-2026-07-22 (P2, user-approved): scope extended with the
engagement sanity check + funded-route documentation; promoted toward Ready.
Incidents recurred twice since filing (2026-07-08 "Insufficient balance" dead
run; 2026-07-18 empty agentic output needing a manual "do NOT use tools" rerun).
Cold-critic BLOCKER-2 resolved in
`.agent/reports/kaizen-session-2026-07-22.plan.md` (funded route evidenced
across 4 sessions; env override + tool fallback chain negate the SPOF concern).

## Files Touched

- scripts/lib/external_agent.sh
- backend/tests/unit/scripts_ci/test_external_agent_model_pin.py
- skills/delivery/qa-agent/config.yaml
- skills/delivery/kaizen-skill/config.yaml

## Test Evidence

uv run pytest tests/unit/scripts_ci/test_external_agent_model_pin.py -> 5 passed (pin default, env override, empty-output retry with no-tools preamble, exit 5 on double-empty, engaged retry success).

## QA Report

Pending.

## Blockers

None.
