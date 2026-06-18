# AE-0218 — Canary test for the transcript `usage` field contract

Status: Intake
Tier: T2
Priority: Low
Type: Quality
Area: Agent Workflow
Owner: Agent
Agent Lane: developer → qa
Branch: TBD
Kanban Card: AE-0218
Created: 2026-06-18
Updated: 2026-06-18
Source: kaizen session-2026-06-18 (K3, class L3) — `.agent/reports/kaizen-session-2026-06-18.plan.md`

## Goal

Make a Claude Code transcript schema change (a renamed/removed `usage` field)
fail **loudly** in tests instead of silently zeroing the context-% reminder.

## Problem

The context-window accounting in `scripts/handoff/context_reminder.py` depends on
**undocumented** transcript `usage` fields (`scripts/handoff/constants.py:USAGE_FIELDS`).
If Claude Code renames one of these fields, the reminder silently computes 0% and
never fires — a quiet failure. The same literals also live in
`~/.claude/statusline-pitao.py` (outside this repo), so cross-root dedup is
impractical; **resilience (a canary), not DRY, is the right lever** (this scope
was corrected mid-kaizen after live-code verification).

## Scope

- Commit a small known-good transcript **fixture** under the handoff tests.
- Add a canary test asserting every `USAGE_FIELDS` key is present in the fixture,
  so a Claude Code field rename breaks the test.
- Keep/refresh the "Limits" note in `docs/guides/smart-handoff.md` documenting the
  undocumented-contract fragility.

## Non-Goals

- Deduplicating against the out-of-repo `~/.claude/statusline-pitao.py` copy
  (impractical; the canary covers the in-repo contract only — state this limit).

## Classification (AE-0153 / AE-0180)

- Quality change. The canary IS the seeded-violation proof: a test asserting the
  canary FAILS when a `USAGE_FIELDS` key is removed from the fixture confirms it
  fires.

## Acceptance Criteria

- [ ] Known-good transcript fixture committed.
- [ ] Canary test asserts all `USAGE_FIELDS` present in the fixture.
- [ ] **Seeded-violation test**: removing a field from the fixture (or adding an
      unknown required field to `USAGE_FIELDS`) makes the canary FAIL.
- [ ] Fragility/limit documented in the guide; mypy + ruff clean.

## References

- Kaizen plan: `.agent/reports/kaizen-session-2026-06-18.plan.md` (K3)
- `scripts/handoff/constants.py` (`USAGE_FIELDS`), `context_reminder.py`
