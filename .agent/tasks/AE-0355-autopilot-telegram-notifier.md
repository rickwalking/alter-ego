# AE-0355 — Notifier protocol + TelegramNotifier (slide album + action keyboard, reminders)

Status: Ready
Tier: T2
Priority: High
Type: Feature
Area: backend
Owner: Grok (Cursor CLI, grok-4.7-high)
Agent Lane: developer → qa → release
Branch: feat/ae-0355-autopilot-telegram-notifier
Kanban Card: TBD
Created: 2026-10-13
Updated: 2026-10-13
Parent: AE-0348

## Goal

When a run is ready for the owner (or fails/escalates/publishes), message the owner on Telegram with slide previews and inline Approve / Rework / Reject buttons.

## Problem

The backend has no outbound notification channel (`notification_service.py` email is a log line).

## Scope

- `Notifier` protocol in `domain/ports.py`: `send_review(ReviewNotice)`, `send_status(StatusNotice)`; `TelegramNotifier` adapter using `httpx.AsyncClient` against `https://api.telegram.org/bot{token}/`.
- Review message: `sendMediaGroup` with up to 10 PT slide JPEGs uploaded as **multipart from disk** (never public URLs; project stays private), first item caption = title + score summary (persona score, sources count). Then `sendMessage` with caption preview (≤1000 chars) + inline keyboard: `✅ Approve` `ap:approve:<run_id>`, `✏️ Rework` `ap:rework:<run_id>`, `🗑 Reject` `ap:reject:<run_id>` (assert each ≤64 bytes). Store message ids in `telegram_message_ids`.
- Status messages: escalated (reason + web UI link), failed, published (permalink), publish_failed (+ `🔁 Retry` `ap:retry:<run_id>`), IG token expiring.
- Trigger: consume `content.autopilot.*` events (outbox relay subscriber or direct call after transition — pick the existing pattern; document choice in Decision Log). Must be at-least-once safe: skip if `telegram_message_ids` already has the review for that revision number.
- Reminder: runs in `awaiting_owner` >24 h get one nudge (tracked to avoid repeats).
- Telegram 429 → honour `retry_after`; other errors → log + retry next tick (max 3).

## Non-Goals

- Handling button presses (AE-0356).
- Other channels (Discord, email).

## Acceptance Criteria

- [ ] WHEN `ready_for_owner` is emitted THE notifier SHALL send one album (≤10 slides) and one keyboard message to `TELEGRAM_OWNER_CHAT_ID`.
- [ ] WHEN the same event is delivered twice THE owner SHALL receive the review only once.
- [ ] WHEN Telegram returns 429 with retry_after THE notifier SHALL wait/re-schedule and not drop the notice.
- [ ] WHEN a run stays awaiting_owner for 24 h THE owner SHALL receive exactly one reminder.
- [ ] WHEN the bot token is unset THE notifier SHALL be a no-op logger and autopilot runs SHALL escalate with reason `notifier_unconfigured`.

## Gherkin Scenarios

```gherkin
Feature: Telegram review notification

  Scenario: Owner receives slides and buttons
    Given an autopilot run became ready for the owner with 7 slides
    When the notifier handles the event
    Then Telegram receives one media group with 7 photos
    And one message with Approve, Rework and Reject buttons

  Scenario: Duplicate event is ignored
    Given the review was already sent for this revision
    When the same event is handled again
    Then Telegram is not called

  Scenario: Rate limited
    Given Telegram answers 429 with retry_after 3
    When the notifier sends the review
    Then it retries after 3 seconds and succeeds
```

## Delta

### ADDED

- `backend/src/rag_backend/modules/autopilot/infrastructure/telegram_notifier.py`
- `backend/src/rag_backend/modules/autopilot/application/notifications.py`
- `backend/tests/features/autopilot_telegram_notify.feature`

### MODIFIED

- settings: `telegram_bot_token`, `telegram_owner_chat_id`

### REMOVED

- None.

## Affected Areas

- Backend
- Tests: respx-mocked Telegram

## Dependencies

- Blocks: AE-0356
- Blocked by: AE-0350, AE-0354

## Implementation Plan

1. Feature first.
2. Protocol + message builders (pure, unit-tested incl. 64-byte callback assert).
3. httpx adapter with respx tests.
4. Event wiring + reminder sweep.

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
- [ ] Bot token never logged (httpx URL contains it — redact in logs)

## Progress Log

### 2026-10-13 00:00

Ticket created from docs/architecture/grokbot-autopilot.md (ticket #6).

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
