# AE-0355 — Notifier protocol + TelegramNotifier (slide album + action keyboard, reminders)

Status: Review
Tier: T2
Priority: High
Type: Feature
Area: backend
Owner: Grok (Cursor CLI, grok-4.7-high)
Agent Lane: developer → qa → release
Branch: feat/ae-0355-autopilot-telegram-notifier
Kanban Card: TBD
Created: 2026-10-13
Updated: 2026-10-14
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

- [x] WHEN `ready_for_owner` is emitted THE notifier SHALL send one album (≤10 slides) and one keyboard message to `TELEGRAM_OWNER_CHAT_ID`.
- [x] WHEN the same event is delivered twice THE owner SHALL receive the review only once.
- [x] WHEN Telegram returns 429 with retry_after THE notifier SHALL wait/re-schedule and not drop the notice.
- [x] WHEN a run stays awaiting_owner for 24 h THE owner SHALL receive exactly one reminder.
- [x] WHEN the bot token is unset THE notifier SHALL be a no-op logger and autopilot runs SHALL escalate with reason `notifier_unconfigured`.

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

### 2026-10-14 00:45

In Development. Feature file, notifier, outbox tick, and tests landed. Gate capture fail=0 (four Postgres gates skipped).

## Files Touched

- `backend/tests/features/autopilot_telegram_notify.feature`
- `backend/src/rag_backend/modules/autopilot/notify_constants.py`
- `backend/src/rag_backend/modules/autopilot/domain/messages.py`
- `backend/src/rag_backend/modules/autopilot/domain/notice_log.py`
- `backend/src/rag_backend/modules/autopilot/domain/notify.py`
- `backend/src/rag_backend/modules/autopilot/domain/ports.py`
- `backend/src/rag_backend/modules/autopilot/domain/exceptions.py`
- `backend/src/rag_backend/modules/autopilot/domain/gate.py`
- `backend/src/rag_backend/modules/autopilot/domain/models.py`
- `backend/src/rag_backend/modules/autopilot/application/notifications.py`
- `backend/src/rag_backend/modules/autopilot/application/runner.py`
- `backend/src/rag_backend/modules/autopilot/infrastructure/telegram_notifier.py`
- `backend/src/rag_backend/modules/autopilot/infrastructure/telegram_payload.py`
- `backend/src/rag_backend/modules/autopilot/infrastructure/slide_files.py`
- `backend/src/rag_backend/modules/autopilot/infrastructure/review_facts.py`
- `backend/src/rag_backend/modules/autopilot/infrastructure/notice_source.py`
- `backend/src/rag_backend/modules/autopilot/infrastructure/ready_notifier.py`
- `backend/src/rag_backend/modules/autopilot/infrastructure/repository.py`
- `backend/src/rag_backend/modules/autopilot/infrastructure/models.py`
- `backend/src/rag_backend/modules/autopilot/bootstrap.py`
- `backend/src/rag_backend/modules/autopilot/public.py`
- `backend/src/rag_backend/modules/autopilot/__init__.py`
- `backend/src/rag_backend/application/workers/workflow_workers.py`
- `backend/src/rag_backend/bootstrap/app_factory.py`
- `backend/src/rag_backend/infrastructure/config/settings.py`
- `backend/.env.example`
- `backend/tests/unit/modules/autopilot/test_telegram_messages.py`
- `backend/tests/unit/modules/autopilot/test_telegram_notifier.py`
- `backend/tests/unit/modules/autopilot/test_owner_notifications.py`
- `backend/tests/unit/modules/autopilot/test_slide_files.py`
- `backend/tests/unit/modules/autopilot/test_notice_log.py`
- `backend/tests/unit/modules/autopilot/test_autopilot_runner.py`
- `backend/tests/unit/application/test_workflow_workers.py`
- `backend/tests/integration/test_autopilot_telegram_ledger.py`
- `backend/tests/integration/test_autopilot_state_machine.py`
- `.agent/reports/AE-0355.dev-summary.md`

## Test Evidence

- `backend/tests/features/autopilot_telegram_notify.feature` (owner album, duplicate, 429, reminder, missing token, escalated link, permalink, retry).
- Unit: `test_telegram_messages.py`, `test_telegram_notifier.py` (respx; token `test-bot-token` never appears in error text), `test_owner_notifications.py`, `test_slide_files.py`, `test_notice_log.py`, `test_autopilot_runner.py`, `test_workflow_workers.py`.
- Integration: `test_autopilot_telegram_ledger.py` (ledger does not move `updated_at`; PT slides; outbox scan; unconfigured tick).
- Local `uv run pytest`: 3193 passed, 7 skipped, 1 failed (unrelated blog-post 409; see Blockers).
- `uv run alembic heads`: single head `f2a3b4c5d6e7`.

## QA Report

Pending.

## Decision Log

- The outbox relay only publishes to Redis. Nothing consumes `content.autopilot.*`, so the worker tick reads the newest 100 rows of that family and dedupes with a notice ledger in `telegram_message_ids`. No Redis subscriber.
- The review revision is the editorial `lock_version` stored on `ready_for_owner`, not `revision_count`.
- A bare JSON list stays valid. After the first notice the column is `{ids, reviews, reminders, statuses, attempts}`. Ledger writes do not change `updated_at`; the reminder clock is that timestamp.
- HTTP 429 sleeps in process when `retry_after` is at most 60 seconds (up to 3 tries) and does not increment the attempt counter. A longer wait is left for the next tick. Other errors stop after 3 attempts.
- One JPEG uses `sendPhoto` (a media group needs 2–10 items). Zero JPEGs still send the keyboard. The reminder repeats Approve / Rework / Reject.
- Unconfigured is an empty bot token or an empty owner chat id. The runner escalates before `awaiting_owner`, because that state has no transition to `escalated`.
- `content.autopilot.ig_token_expiring` is rendered when present. No token refresher in this ticket (AE-0358).
- Telegram constants are in `notify_constants.py` so `constants.py` stays under 400 lines.

## Blockers

- Manual (Pedro): set `TELEGRAM_BOT_TOKEN` and `TELEGRAM_OWNER_CHAT_ID` (empty placeholders are in `backend/.env.example`). `AUTOPILOT_ENABLED` and `AUTOPILOT_OWNER_USER_ID` are still required from AE-0354. GitHub Secrets, `deploy.yml`, and compose wiring are AE-0359.
- Unrelated local pytest failure, not touched by this ticket and not a gate failure (the test gate skipped because `DATABASE_URL` is unset): `tests/integration/test_blog_post_management_ae0296.py::TestDeleteGuards::test_delete_with_stale_version_is_409`.

## Final Summary

The owner gets one Telegram review (slides plus Approve / Rework / Reject), status messages, and a single 24 hour reminder. Replays and a missing bot token do not double-send or invent a delivery. Button presses remain AE-0356.
