# AE-0217 — Hook authoring rule + reusable clean-stdout test helper

Status: Intake
Tier: T2
Priority: Medium
Type: Quality
Area: Agent Workflow
Owner: Agent
Agent Lane: developer → qa
Branch: TBD
Kanban Card: AE-0217
Created: 2026-06-18
Updated: 2026-06-18
Source: kaizen session-2026-06-18 (K2, class L2) — `.agent/reports/kaizen-session-2026-06-18.plan.md`

## Goal

Make the Claude Code hook-authoring contract explicit and enforced, so a future
hook cannot silently corrupt the harness by writing non-JSON to stdout.

## Problem

During AE-0216 we hit the root cause that hook commands must emit **clean
stdout**: `uv run` can sync-print to stdout and corrupt the hook's JSON payload,
breaking the harness. The fix used (stdlib-only `python3`, never `uv run`) is
currently tribal knowledge — written nowhere durable, so the next hook author
re-learns it the hard way.

## Scope

- Document the rule in `docs/guides/smart-handoff.md` (and/or a harness
  `AGENTS.md`): hook commands are **stdlib-only `python3`, never `uv run`**; a
  hook MUST print valid JSON or nothing to stdout.
- Generalize the ad-hoc per-hook stdout assertions in
  `scripts/handoff/tests/` into a **reusable test helper** that asserts a hook
  emits parseable-JSON-or-empty on every input class (valid payload, malformed
  stdin, empty stdin, unexpected fields), so new hooks inherit the check.

## Non-Goals

- Changing existing hook behavior (the current hooks already comply).
- A CI gate scoped to repo-root `scripts/` (out of scope; tests run via the
  backend uv/pytest env as today).

## Classification (AE-0153 / AE-0180)

- Quality/tooling change. Per AE-0180 this ships a **rule-fires regression
  test**: the helper must be proven to FAIL on a seeded violating hook (one that
  prints stray text to stdout), not merely pass on the compliant hooks.

## Acceptance Criteria

- [ ] Hook-authoring rule documented (stdlib-only `python3`, JSON-or-empty stdout).
- [ ] Reusable clean-stdout test helper exists and is applied to all hooks in
      `scripts/handoff/`.
- [ ] **Seeded-violation test**: a deliberately non-compliant hook fixture
      (prints non-JSON to stdout) makes the helper FAIL — proving the check fires.
- [ ] Existing 36 handoff tests still pass; mypy + ruff clean.

## References

- Kaizen plan: `.agent/reports/kaizen-session-2026-06-18.plan.md` (K2)
- Exemplars: `scripts/handoff/tests/test_inject_handoff.py`
- Standard: `docs/guides/qa-checkpoints.md` → Rule-fires regression test (AE-0180)
