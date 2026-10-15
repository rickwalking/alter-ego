# AE-0392 — Autopilot content gate: repair first, report real reasons

Status: In Development
Tier: T1
Priority: P0
Type: Bugfix
Area: backend
Owner: Claude Code (claude-opus-5-5)
Agent Lane: developer → qa → release
Branch: fix/ae-0392-content-gate-repair-first
Kanban Card: TBD
Created: 2026-10-15
Updated: 2026-10-15
Parent: AE-0348

## Goal

The autopilot content (and design) gate repairs deterministic content-quality violations
itself, approves when that makes the gate clean, and otherwise revises with feedback that says
exactly which slide, rule and text failed.

## Problem

Prod carousel `f21b2bdb-2cdc-460e-8542-6b7c92682f4c` (2026-10-15): a ~95 min GLM content run
produced 7 drafts, then the gate revised with "Reason: forbidden_phrase. Measured: ." and the
whole content phase regenerated (~60 more min) with no information about what failed.

Root cause: `modules/autopilot/domain/snapshot.py` `_forbidden()` merged the forbidden-phrase
hits, every blocking `content_gate_validation` violation code and the phrase scan into one
list, so any AE-0366 v3 blocking rule (sentence case, empty body, EN == PT, item counts, tag
balance) surfaced as `forbidden_phrase`, and the revise template rendered an empty Measured.
The editorial graph state has no forbidden-phrase channel at all, so in prod
`forbidden_phrase` could only come from those folded-in validator codes.

## Scope

- New reason `content_quality` for blocking presentation rules; `forbidden_phrase` only for
  real phrase hits. Measured: the phrases, or `rule@slide` pairs (max 10); never empty.
- Revise feedback v2 prompt (`agents/prompts/autopilot/v2/revise_feedback.yaml`) with one line
  per failing slide (slide, locale, field, rule, current text) and "fix only these slides".
- Repair before revise at the content and design gates: the AE-0367 owner autofix plan runs on
  the checkpoint `localized_slides` through the editorial facade (`run_gate_repair` →
  `OwnerAutofixService.repair_gate`), under the project lock + lock-version CAS; the gate is
  read again and approved when clean (no revision spent). Also before an escalation at the cap.
  Log `autopilot_content_autorepaired` with the fixed rules.
- Targeted re-draft: the engine has no per-slide regeneration behind a review decision
  (structured feedback is final-review only), so the fallback whole-phase revise carries the
  specific per-slide violations. The content phase's own AE-0309 per-slide re-draft still runs.

## Non-Goals

- No DB migration.
- No change to the engine's content regeneration (per-slide revise is a follow-up).
- Final review is unchanged: it stops for the owner, whose 🛠 Fix issues (AE-0367) covers it.

## Acceptance Criteria

- [x] A v3 violation is reported as `content_quality` with `rule@slide` in Measured.
- [x] A casing-only violation is auto-repaired and the gate approved without a revise.
- [x] An empty-body violation the repair can fill is approved.
- [x] A non-repairable violation gets a revise whose feedback names slide, rule and text.
- [x] A real forbidden phrase still revises as `forbidden_phrase` with the phrase in Measured.
- [x] Same treatment at the design gate; repair also precedes escalation at the cap.
- [x] Integration test on the real editorial engine with a fake LLM.
- [ ] Python 3.11 import check (relayed to the orchestrator).

## Gherkin Scenarios

`backend/tests/features/autopilot_content_quality_gate_ae0392.feature`

## Repro Steps

1. Autopilot run reaches the content gate with a lowercase PT heading on slide 5.
2. Before: revise with "Reason: forbidden_phrase. Measured: ." → full content regeneration.
3. After: heading repaired in the checkpoint, gate approved, no revision counted.

## Affected Areas

- [x] Backend (autopilot module, editorial facade, carousel owner-autofix service, prompts)
- [ ] Frontend
- [x] Tests

## Dependencies

- AE-0366 (blocking validator, `repair_casing`), AE-0367 (owner autofix plan), AE-0309
  (fail-closed content chain), AE-0363 (run-owned resume).

## Progress Log

### 2026-10-15

Ticket created (hotfix fast path). Implemented reason split, v2 feedback, gate repair through
the editorial facade, runner wiring, docs, Gherkin + tests. See
`.agent/reports/AE-0392.dev-summary.md`.

## Files Touched

- `backend/src/rag_backend/modules/autopilot/` (domain/gate, domain/quality (new),
  domain/snapshot, domain/policy, domain/autofix, application/feedback,
  application/gate_repair (new), application/runner, infrastructure/content_autofixer,
  bootstrap, constants, quality_constants (new))
- `backend/src/rag_backend/application/services/carousel/owner_autofix_{service,source,gate}.py`
- `backend/src/rag_backend/domain/constants/carousel_autofix.py`
- `backend/src/rag_backend/modules/editorial/infrastructure/carousel_owner_autofix.py`, `public.py`
- `backend/src/rag_backend/agents/prompts/autopilot/v2/` (new prompt + README)
- Tests: `tests/unit/application/*ae0392*`, `tests/unit/modules/autopilot/test_content_quality_gate_ae0392.py`,
  `tests/unit/modules/autopilot/test_gate_snapshot.py`, feature file
- Docs: `docs/architecture/grokbot-autopilot.md`

## Test Evidence

See `.agent/reports/AE-0392.dev-summary.md`.

## QA Report

Pending.

## Blockers

None.
