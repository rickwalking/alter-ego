# AE-0367 — Telegram fix-issues button with deterministic content repair

Status: In Development
Tier: T1
Priority: P0
Type: Bugfix
Area: backend
Owner: Claude Code (claude-opus-5-5)
Agent Lane: developer → qa → release
Branch: fix/ae-0367-telegram-fix-issues
Kanban Card: TBD
Created: 2026-10-14
Updated: 2026-10-14
Parent: AE-0348

## Goal

When an autopilot carousel reaches the owner on Telegram with quality issues, the review
message lists them and a `🛠 Fix issues` button repairs them deterministically (no manual
editing, no scripts, no LLM regeneration of a whole phase), re-renders, and sends a fresh review.

## Problem

AE-0366 made the content-quality rules blocking and fixed the root causes, but carousels that
already reached final review (or slip through) still need a manual edit or a hand-run script to
fix lowercase headings, a title-only slide, an untranslated EN slide or mangled `<strong>` tags.
The owner only has Approve / Rework / Reject; Rework regenerates a whole phase with the LLM.

## Scope

- Review message: up to 5 quality-issue lines from the AE-0366 validator over the persisted
  slides (plus untranslated-EN and proper-noun findings), e.g. "Slide 5: heading starts
  lowercase".
- A 4th keyboard button `🛠 Fix issues` (`ap:fix:<run_id>`) when something is fixable.
- Webhook: owner allowlist + `update_id` dedupe; "nothing to fix" answer on a clean carousel;
  otherwise CAS `awaiting_owner → reworking` (reason `owner_autofix`), queue the fix on the run
  row, edit the old keyboard to "Superseded by fixed version".
- Worker tick (AE-0363 pattern): deterministic repairs on the slide rows and the workflow
  presentation copy (sentence case PT/EN incl. items, proper nouns from the carousel's own
  vocabulary + a constants list, features from `key_points`, summary points from the outline,
  `<strong>` balancing), one bounded LLM re-translate for untranslated EN fields only (retry,
  keep current EN on failure), re-validate, republish (new artifact version, hero images kept),
  then the normal final-review stop sends the new album + review (state back to
  `awaiting_owner`).

## Non-Goals

- No DB migration (the fix is queued in the existing `rework_phase` column).
- No LLM regeneration of any phase; hero images are never regenerated.
- No change to the Approve / Rework / Reject flows.

## Acceptance Criteria

- [x] Review message lists at most 5 issue lines; the keyboard has `🛠 Fix issues` only when
  something is fixable.
- [x] A non-owner tap changes nothing; a double tap queues and runs the fix once; a clean
  carousel answers "Nothing to fix" and keeps the review open.
- [x] Each repair has a unit test: first-letter capitalization, proper nouns from the carousel
  vocabulary, features from key_points, summary points, `<strong>` balancing, untranslated-EN
  detection.
- [x] Integration test on the real editorial engine (fake renderer + fake LLM): lowercase /
  empty fixtures → tap fix → rows fixed → render called → new review sent.
- [x] EN re-translate failure keeps the current EN and the new review still lists it.
- [ ] Python 3.11 import check.

## Gherkin Scenarios

`backend/tests/features/autopilot_owner_autofix.feature`

## Affected Areas

- [x] Backend (autopilot module, editorial facade, carousel application services, prompts)
- [ ] Frontend
- [x] Tests

## Dependencies

- Builds on AE-0366 (blocking validator, `repair_casing`, `project_localized_copy_to_database`).
- AE-0363 (queued rework on the worker tick), AE-0313 (republish).

## Progress Log

### 2026-10-14

Ticket created (hotfix fast path, owner decision). Implemented: editorial owner-autofix
service + facade seam, autopilot webhook/worker/notifier wiring, versioned re-translate prompt,
Gherkin + 103 tests. Rebased onto origin/main. All 16 static backend gates PASS on the Pi;
DB gates and the Python 3.11 import check relayed to the orchestrator. See
`.agent/reports/AE-0367.dev-summary.md`.

## Files Touched

- `backend/src/rag_backend/application/services/carousel/owner_autofix_*.py` (new)
- `backend/src/rag_backend/domain/constants/carousel_autofix.py` (new)
- `backend/src/rag_backend/agents/prompts/carousel_autofix/v1/` (new prompt + README)
- `backend/src/rag_backend/modules/editorial/infrastructure/carousel_owner_autofix.py` (new), `public.py`
- `backend/src/rag_backend/modules/autopilot/` (domain/autofix, review_issues, content_autofixer,
  owner_actions, owner_steps, rework_step, runner, notifications, review_facts, telegram_notifier,
  bootstraps, constants)
- `backend/src/rag_backend/bootstrap/autopilot_worker_factory.py`,
  `application/services/carousel/editorial_workflow_service.py` (`chat_model`),
  `application/services/carousel_template/prompts.py`
- Tests: `tests/unit/application/*ae0367*`, `tests/unit/modules/autopilot/test_owner_autofix_ae0367.py`,
  `tests/features/autopilot_owner_autofix.feature`
- Docs: `docs/architecture/grokbot-autopilot.md`

## Test Evidence

See `.agent/reports/AE-0367.dev-summary.md`.

## QA Report

Pending.

## Blockers

None.
