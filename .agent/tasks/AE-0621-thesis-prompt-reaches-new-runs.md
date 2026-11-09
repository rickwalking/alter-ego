# AE-0621 — Thesis prompt reaches a new run when older prompted runs still wait

Status: Dev Complete
Tier: T1
Priority: High
Type: Bug
Area: Backend
Owner: Claude
Branch: fix/thesis-prompt-scan-starvation
Created: 2026-11-09
Updated: 2026-11-09

## Goal

Every POV run in `awaiting_thesis` gets its Telegram thesis prompt, however many older runs are still waiting.

## Problem

On 2026-11-09 the owner tapped "Gerar agora" on a `pov_news` theme. The run moved to `awaiting_thesis`, but the
thesis prompt never reached Telegram, so the carousel was never generated and never entered the generation queue.

`ThesisPromptService.tick` read only the 10 oldest `awaiting_thesis` runs (`THESIS_SCAN_LIMIT = 10`, ordered by
`updated_at`). Saving the notice ledger leaves `updated_at` alone, so 10 runs that were already prompted and are still
waiting filled the page forever and the 11th run was never prompted. It only cleared when an old run expired (72 h)
or was answered.

## Scope

- Scan every waiting run in the thesis prompt tick (bounded by a guard against a runaway backlog).
- Regression test with 10 prompted runs plus a new one, on a fake that honours `limit` like the SQL repository.

## Non-Goals

- Do not refactor unrelated code
- "Aprovar todas" (`APPROVE_ALL_LIMIT`) keeps its 10-run page; the new run still gets its own prompt.

## Acceptance Criteria

- [x] With 10 already-prompted runs waiting, a newer unprompted run gets exactly one prompt on the next tick.
- [x] A run is still prompted only once.

## Repro Steps

1. Have 10 runs in `awaiting_thesis` that were already prompted.
2. Queue a POV run (for example via "Gerar agora").
3. The run reaches `awaiting_thesis`; no thesis prompt is sent.

## Affected Areas

- [x] Backend
- [ ] Frontend
- [x] Tests

## Dependencies

None.

## Progress Log

### 2026-11-09 16:20

Diagnosed on prod (11 runs awaiting thesis, the newest never prompted). The stuck run was confirmed with its draft
thesis by hand and is generating. Fix and regression test written; hotfix fast path.

## Files Touched

- `backend/src/rag_backend/modules/autopilot/application/thesis_prompts.py`
- `backend/tests/features/autopilot_pov_thesis.feature`
- `backend/tests/unit/modules/autopilot/test_thesis_prompt_scan_ae0621.py` (new)
- `.agent/tasks/AE-0621-thesis-prompt-reaches-new-runs.md` (new)

## Test Evidence

- New test fails with `THESIS_SCAN_LIMIT = 10` and passes with the fix.
- `tests/unit/modules/autopilot`: 1146 passed.
- Backend gates run individually and green: format, lint, lint-diff, blanket-ignore, strict-diff, type, imports,
  arch-ratchet, docstrings, dead-code, inline-prompts, gherkin-refs, comments, blog-v1-dead-code, redis-factory,
  autopilot-env, healthcheck-loopback, openapi-fresh, bandit, integrity, duplication.
- Python 3.11 import check: ok.
- test / diff-cover / migrations / schema-drift: no local Postgres; CI.
- mutation: deferred to CI (hotfix fast path).

## QA Report

Pending (hotfix fast path).

## Blockers

None.
