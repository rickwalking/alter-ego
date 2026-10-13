# AE-0356 — Telegram webhook: secret header, owner allowlist, dedupe, Approve / Rework / Reject / Retry

Status: Ready
Tier: T2
Priority: Critical
Type: Feature
Area: backend
Owner: Grok (Cursor CLI, grok-4.7-high)
Agent Lane: developer → qa → release
Branch: feat/ae-0356-autopilot-telegram-webhook-actions
Kanban Card: TBD
Created: 2026-10-13
Updated: 2026-10-13
Parent: AE-0348

## Goal

Turn the owner's Telegram button presses (and rework text) into safe, exactly-once workflow actions.

## Problem

This endpoint is the ONLY path to publishing; it must be impossible to trigger by anyone but the owner, and double taps / Telegram retries must not double-act.

## Scope

- `POST /api/telegram/webhook` (no JWT, no API key): require header `X-Telegram-Bot-Api-Secret-Token` == `TELEGRAM_WEBHOOK_SECRET` (constant-time) else 401; always return 200 quickly for valid secret.
- Dedupe: insert `update_id` into `telegram_updates`; on conflict → return 200, do nothing.
- Allowlist: `callback_query.from.id` / `message.from.id` must equal `TELEGRAM_OWNER_CHAT_ID`; else ignore silently (200).
- Parse `ap:<action>:<run_id>` strictly (regex, UUID); unknown → `answerCallbackQuery` 'unknown action'.
- Approve: CAS `awaiting_owner → publishing`; resume `approve` on final_review (editorial facade) → `approved_for_publish`; release `is_public=true` (publishing facade `CarouselReleaseCommand`); enqueue IG publish (AE-0357). CAS failure → answer 'already handled'.
- Rework: CAS `awaiting_owner → reworking`; send keyboard Text | Design | Images | Outline (`ap:rw:<phase>:<run_id>` → map Text→content); then `ForceReply` 'What should change?'; store pending (run_id, phase) keyed by owner; next owner text message = feedback → resume `revise` with `structured_feedback.target_phase` + feedback; runner (AE-0354) re-drives gates back to final_review → `awaiting_owner`. Revision cap 409 → `escalated`.
- Reject: CAS `awaiting_owner → rejected`; project stays private.
- Retry: CAS `publish_failed → publishing`; enqueue publish.
- Always `answerCallbackQuery`; edit the keyboard message to the outcome text (removes buttons).
- Ops helper: `python -m rag_backend.modules.autopilot.scripts.set_webhook` calls `setWebhook` with url + secret_token + `allowed_updates=["message","callback_query"]`.

## Non-Goals

- Group chats, multiple approvers.
- Editing slides from Telegram.

## Acceptance Criteria

- [ ] WHEN the secret header is missing or wrong THE webhook SHALL return 401 and take no action.
- [ ] WHEN a non-owner presses a button THE webhook SHALL take no action.
- [ ] WHEN the owner taps Approve twice (or Telegram redelivers) THE system SHALL publish exactly once.
- [ ] WHEN the owner taps Rework → Images and types feedback THE images phase SHALL re-run with that feedback and a new review SHALL arrive.
- [ ] WHEN the owner taps Reject THE project SHALL remain `is_public=false` and nothing SHALL be published.
- [ ] WHEN Approve is pressed on a run not in `awaiting_owner` THE owner SHALL see 'already handled' and nothing changes.

## Gherkin Scenarios

```gherkin
Feature: Owner actions via Telegram

  Scenario: Approve publishes once
    Given a run awaiting the owner
    When the owner taps Approve twice
    Then final_review is approved once
    And one Instagram publish job is enqueued

  Scenario: Forged request
    When a webhook call arrives without the secret token header
    Then the response status is 401
    And no run changes state

  Scenario: Stranger presses a button
    Given a callback from a user who is not the owner
    When the webhook handles it
    Then no run changes state

  Scenario: Rework with feedback
    Given a run awaiting the owner
    When the owner taps Rework, chooses Images and replies "darker palette, no robots"
    Then the images phase is revised with that feedback
    And the run returns to awaiting the owner after regeneration

  Scenario: Reject
    When the owner taps Reject
    Then the run is "rejected" and the carousel stays private
```

## Delta

### ADDED

- `backend/src/rag_backend/modules/autopilot/api/telegram_webhook.py`
- `backend/src/rag_backend/modules/autopilot/application/owner_actions.py`
- `backend/src/rag_backend/modules/autopilot/scripts/set_webhook.py`
- `backend/tests/features/autopilot_owner_actions.feature`

### MODIFIED

- settings: `telegram_webhook_secret`
- nginx: ensure `/api/telegram/webhook` is proxied (it is under `/api/`)

### REMOVED

- None.

## Affected Areas

- Backend
- API: public webhook
- Security: secret header + allowlist
- Tests

## Dependencies

- Blocks: AE-0359
- Blocked by: AE-0354, AE-0355, AE-0357

## Implementation Plan

1. Feature first.
2. Parser + allowlist + dedupe as pure/unit-tested pieces.
3. Action handlers with CAS; integration tests incl. concurrent double-approve (asyncio.gather).
4. set_webhook script.

## Implementer Notes (read first — Cursor CLI / Grok)

- Source of truth: [docs/architecture/grokbot-autopilot.md](../../docs/architecture/grokbot-autopilot.md) and [ADR-0020](../../docs/decisions/0020-grokbot-autopilot.md). If this ticket and the doc disagree, STOP and ask — do not guess.
- Read `CLAUDE.md`, `backend/CLAUDE.md`, `backend/AGENTS.md`, `docs/architecture/module-conventions.md` before coding.
- Module rules: new code lives in `backend/src/rag_backend/modules/autopilot/` following `modules/_template/` (domain/application/infrastructure/api + `public.py` + `bootstrap.py` + `constants.py`). Other modules are reached ONLY through their `public.py`; add an import-linter contract for `autopilot` (module-conventions §7a/§7d).
- Hard rules: no magic strings (constants.py), no `Any`/`object`, ≤3 args per function (Pydantic/typed command objects), guard clauses, ≤400 lines/file, mypy strict, ruff clean, 90%+ branch coverage.
- Behavior-changing tickets: write the `.feature` file FIRST under `backend/tests/features/` and reference scenario names in test comments.
- Never commit secrets. Never push `main` (auto-deploys prod). Branch per ticket, lowercase conventional commits.
- Done = `bash scripts/ci/gate-capture.sh backend` green with the `GATES_JSON:` line pasted in the dev summary + `/qa-agent` PASS. Never pipe gates to `tail`/`head`.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked
- [ ] OWASP: auth bypass attempts tested (no header, wrong header, non-owner, malformed callback_data)
- [ ] Concurrent double-approve test present

## Progress Log

### 2026-10-13 00:00

Ticket created from docs/architecture/grokbot-autopilot.md (ticket #7).

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Decision Log

See ADR-0020.

## Blockers

None.

## Final Summary

Pending.
