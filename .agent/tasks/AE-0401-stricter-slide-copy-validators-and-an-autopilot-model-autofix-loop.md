# AE-0401 — Stricter slide copy validators and an autopilot model autofix loop

Status: In Development
Tier: T1
Priority: P0
Type: Bug
Area: backend
Owner: Claude (owner-requested hotfix)
Agent Lane: developer → qa → release
Branch: fix/ae-0401-validators-model-autofix
Kanban Card: TBD
Created: 2026-10-16
Updated: 2026-10-16

## Goal

Raw JSON, markup leaks, chatter, placeholders, garbled or truncated copy and wrong-language copy never reach an owner as a valid slide, and the autopilot fixes what one model call can fix instead of regenerating the whole phase or escalating.

## Problem

Prod carousel 98a2e2f0 (autopilot run b241ded5, 2026-10-16): slide 3 was a ```` ```json ```` fenced bilingual blob shown as copy, caught only by an accidental casing rule; slide 8's PT body started with `## Checklist para salvar`; the hook's body repeated its heading; a summary point was cut into "Comece com dois ou" / "Três agentes, não dez."; the EN casing read "decide: Pass or return". At the design gate the autopilot logged a gate-repair no-op every minute for ~50 minutes without revising or escalating. The AE-0392 path (deterministic repair, then a whole-phase revise of ~15 min, cap 2, then escalate) escalated text one model call could fix.

## Scope

- 11 blocking copy-hygiene rules (`presentation_copy_rules.py`, `copy_hygiene_text.py`): `structured_payload_in_copy`, `markup_leak`, `emphasis_unbalanced`, `assistant_chatter`, `placeholder_text`, `encoding_garbled`, `copy_truncated`, `body_too_short`, `wrong_language`, `repeated_text`, `structured_item_split`; severities in `pov_hook_v1.yaml` and `hero_lower_third_v4.yaml`.
- Deterministic repair (`copy_hygiene_repair.py`) in the generation-time review repair and the owner/gate autofix plan; EN no-capital-after-colon; key-point split never on a connector.
- Autopilot model fix (`slide_autofix.py`) after the gate repair, through the editorial facade `run_slide_fix` (`slide_fix_service.py`, `slide_fix_loop.py`, `slide_fix_targets.py`, `slide_fix_prompt.py`), prompt `agents/prompts/carousel/v1/slide_fix.yaml`; escalation detail on the state-changed event and the Telegram message; `AUTOPILOT_AUTOFIX_ATTEMPTS` (default 3).

## Non-Goals

- Revising or regenerating the phase for content-quality failures (owner decision: escalate after the fix gives up).
- Changing v1-v3 contracts or existing prompt files.

## Acceptance Criteria

- [x] AC1: Each new rule fires on its seeded violation (PT and EN, heading/body/items) and blocks; the approved 9-slide prod deck passes every rule.
- [x] AC2: `**bold**` and balanced `<strong>` are never flagged (addendum 1).
- [x] AC3: The deterministic repair restores the deck prod shipped (fenced blob, `##` heading) without a model; fenced blob item lists are kept whole.
- [x] AC4: A hook whose body repeats its heading blocks; the fix prompt asks the hook for a distinct subline.
- [x] AC5: The EN repair does not capitalize after a mid-sentence colon.
- [x] AC6: A gate still failing on content quality or a low per-slide voice score gets up to 3 model attempts per slide (parallel, fast role), each fed the remaining violations; a model error or unparseable answer counts as an attempt.
- [x] AC7: Fixed slides are persisted through the reviewer-edit path plus their re-scored voice, under the lock + CAS; a lost CAS writes nothing.
- [x] AC8: Clean gate → approve; otherwise escalate with every failing slide (rule, text, "3 fix attempts"); never a revise for content quality; a repair no-op cannot loop.
- [x] AC9: `autopilot_slide_autofix` per attempt; Langfuse `phase=autofix`, `agent_name=slide_fixer`.
- [x] AC10 (addendum 2): the slide rows are projected from the localized copy every time it is built or changed (content/design ensure, gate repair, model fix); a long `draft_text` never reaches the render.
- [x] AC11 (addendum 2): empty item lists are symmetric on PT/EN (no `translation_shape_mismatch`).
- [x] AC12 (addendum 2): "the code"/"the bot" are not flagged as lowercased "Claude Code"/"Grok Bot".
- [x] AC13 (addendum 2): the POV hook sub-line is at most 40 characters / 1 line; the model fix targets it.

## Gherkin Scenarios

- `backend/tests/features/slide_copy_validators_ae0401.feature`
- `backend/tests/features/autopilot_slide_autofix_ae0401.feature`

## Delta

### ADDED

- `application/services/carousel/{copy_hygiene_text,copy_hygiene_repair,presentation_copy_rules,owner_autofix_lock,slide_fix_types,slide_fix_targets,slide_fix_prompt,slide_fix_loop,slide_fix_service}.py`
- `modules/editorial/infrastructure/carousel_slide_fix.py`
- `modules/autopilot/{autofix_constants.py,application/gate_read.py,application/slide_autofix.py,domain/escalation_detail.py}`
- `domain/constants/slide_fix.py`, `agents/prompts/carousel/v1/slide_fix.yaml`
- `docs/backend/slide-copy-validators.md`, the two feature files and their tests
- `application/services/carousel/localized_rows_sync.py`, `test_rows_follow_localized_ae0401.py`

### MODIFIED

- Validation/repair wiring: `presentation_validation.py`, `presentation_content_rules.py` (helpers public), `presentation_review_repair.py`, `owner_autofix_plan.py`, `owner_autofix_fill.py`, `owner_autofix_service.py` (lock extracted)
- Contracts `pov_hook_v1.yaml`, `hero_lower_third_v4.yaml`; `carousel_presentation.py`
- Rows/projection: `editorial_distribution_persist.py` (`_symmetric_translation`), `phase_artifact_runner.py`, `owner_autofix_vocabulary.py` (multi-word names)
- Autopilot: `gate_repair.py`, `runner.py`, `domain/{autofix,gate,models,messages}.py`, `notifications.py`, `repository.py`, `content_autofixer.py`, `bootstrap.py`, constants
- `persona_agent.py` (`style_guide()`), `settings.py`, `autopilot_worker_factory.py`, `carousel_template/prompts.py`, `modules/editorial/public.py`
- `docs/architecture/grokbot-autopilot.md`, `backend/CLAUDE.md`

### REMOVED

- None.

## Affected Areas

- Backend: presentation validation, autofix, autopilot runner
- Frontend: none
- Database: none (the detail rides in the existing outbox payload)
- API: none
- Tests: unit + feature
- Docs: autopilot architecture, new validator doc
- Prompts/LLM: new `carousel/v1/slide_fix.yaml`; contract rubric text
- Observability: new log events, Langfuse metadata
- Deployment: optional `AUTOPILOT_AUTOFIX_ATTEMPTS` (defaults to 3)

## Dependencies

- Blocks: none
- Blocked by: AE-0400 (PR #116, stacked)
- Related: AE-0366, AE-0367, AE-0392, AE-0397, AE-0398

## Implementation Plan

1. Rules + detectors + contract severities.
2. Deterministic repair, wired into both repair paths.
3. Editorial slide-fix service + facade.
4. Autopilot step after the gate repair; escalation detail.
5. Tests, features, docs.

## QA Checklist

- [x] Security reviewed (model output parsed with `json.loads` / `ast.literal_eval`, never executed)
- [x] Code quality reviewed
- [x] Acceptance criteria validated
- [x] Edge cases tested
- [x] Orphan/unfinished code checked

## Progress Log

### 2026-10-16

Owner request after run b241ded5. Orchestrator addendum the same day: `<strong>`/`**` are legit emphasis; four more prod failures (hook heading = body, EN colon casing, gate repair no-op loop, cut summary point). Addendum 2 (16:35): rows rendered the long draft text instead of the validated localized copy; empty-list PT/EN asymmetry; proper-noun false positives; hook sub-line length. Merged main (AE-0399, AE-0400, AE-0402).

## Files Touched

See Delta.

## Test Evidence

See `.agent/reports/AE-0401.dev-summary.md`.

## QA Report

Pending (hotfix fast path: CI Test & Coverage decides).

## Decision Log

See the dev summary "Decisions".

## Blockers

None.

## Final Summary

Pending.
