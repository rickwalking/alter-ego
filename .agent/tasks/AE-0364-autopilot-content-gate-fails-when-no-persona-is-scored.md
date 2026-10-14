# AE-0364 — Autopilot content gate fails when no persona is scored

Status: Intake
Tier: T1
Priority: P0
Type: Bugfix
Area: backend
Owner: Claude Code (claude-opus-5-5)
Branch: fix/ae-0364-autopilot-persona-unscored
Created: 2026-10-14
Updated: 2026-10-14
Parent: AE-0348

## Goal

The autopilot content gate follows the engine's rule: with no persona scores the voice check is
skipped (forbidden phrases and engine blockers still apply), and the owner's review says
`Persona: not scored`.

## Problem

Prod 2026-10-14, carousel `8e350d6e-78fc-436c-ab95-bed02535198b`: the content phase produced 7
drafts with `persona_scores = {}`; the workflow shows `revisions = {'outline': 2, 'content': 2}`
and the content gate escalates at the cap.

- The autopilot policy `_content` (`modules/autopilot/domain/policy.py`) treated
  `persona_score is None` as a failure (`persona_score_below_threshold`).
- The engine (`validate_content_approve_persona_score` in
  `application/services/carousel/editorial_workflow_service_helpers.py`) allows the approve when
  `persona_scores` is empty or not a dict, and enforces ≥ 70 only when scores exist.
- The autopilot never attaches a persona, so scores are always empty and every autopilot run
  escalated at content.

## Scope

- Policy `_content`: skip the voice floor when there are no scores; keep ≥ 70 when there are.
- Snapshot `_persona_score`: `None` only when there are no scores (missing / empty / not a dict,
  matching the engine). A present entry that is unreadable counts as 0 (fail closed), like a
  missing `overall` (QA r1 B1).
- Telegram review caption: `Persona: not scored` (`LABEL_PERSONA_NOT_SCORED`), scored runs read
  `Persona: 75`.
- Gherkin + unit + integration tests; doc `docs/architecture/grokbot-autopilot.md`.

## Non-Goals

- Do not refactor unrelated code.
- Attaching a persona to autopilot projects (investigated only; follow-up in the dev summary).
- No migration. Nothing run against prod.

## Acceptance Criteria

- [x] Empty `persona_scores` → APPROVE when nothing else blocks; the engine agrees.
- [x] Scores with a lowest overall of 62 → REVISE `persona_score_below_threshold`; the engine
  refuses too.
- [x] Scores of 75 → APPROVE.
- [x] Unscored run still revises on a forbidden phrase or an engine blocker.
- [x] Unreadable present entry → 0 → REVISE.
- [x] Integration: real `EditorialWorkflowService` (fake LLM), content gate with no persona is
  approved by the autopilot and the workflow waits at `design/awaiting_human`.
- [x] Review caption reads `Persona: not scored`.
- [x] Gherkin scenarios in `backend/tests/features/autopilot_runner.feature`.
- [x] Remaining gates (design, images, final review) swept for the same mismatch.
- [x] Python 3.11 import check.

## Repro Steps

1. Autopilot carousel (no persona) reaches `content/awaiting_human` with drafts and
   `persona_scores = {}`.
2. Before the fix: `decide()` → REVISE `persona_score_below_threshold`, then ESCALATE at the cap
   (the new tests fail on the old policy: 8 failures).

## Affected Areas

- [x] Backend
- [ ] Frontend
- [x] Tests

## Dependencies

AE-0363 (merged).

## Gate sweep (requirement 5)

- **design:** the engine never blocks a design approve; the policy fails closed on
  `presentation_validation` blockers or a missing report. Not the same class: the pipeline always
  writes the report (content phase `build_fail_closed_review_updates`, including the empty
  "valid" report, and the design ensure re-validates localized slides), so the field exists on a
  real run.
- **images:** the engine has no images-approve check; the policy needs one present JPEG per
  slide. The pipeline writes `slide_*.jpg` per slide; AE-0362 already aligned count and size.
- **final_review:** the policy always stops (owner decides); no field read.
- **content, other fields:** forbidden-phrase keys are read leniently (absent → no hits), so not
  stricter than the pipeline output; the engine refusal is the engine's own check.
- **research / outline:** policy-only checks on fields the pipeline produces
  (`research_findings`, `outline`); outline count was aligned in AE-0362.

## Progress Log

### 2026-10-14

Ticket created from the prod incident. Fix, tests (new tests fail on the old policy), doc.
Hotfix fast path gates; see the dev summary.

## Files Touched

- `backend/src/rag_backend/modules/autopilot/domain/policy.py`
- `backend/src/rag_backend/modules/autopilot/domain/snapshot.py`
- `backend/src/rag_backend/modules/autopilot/domain/messages.py`
- `backend/src/rag_backend/modules/autopilot/notify_constants.py`
- `backend/tests/unit/modules/autopilot/test_persona_unscored_ae0364.py` (new)
- `backend/tests/integration/test_autopilot_persona_unscored.py` (new)
- `backend/tests/unit/modules/autopilot/test_gate_policy.py`
- `backend/tests/unit/modules/autopilot/test_telegram_messages.py`
- `backend/tests/features/autopilot_runner.feature`
- `docs/architecture/grokbot-autopilot.md`

## Test Evidence

See `.agent/reports/AE-0364.dev-summary.md` (GATES_JSON line).

## QA Report

Pending.

## Blockers

None.
