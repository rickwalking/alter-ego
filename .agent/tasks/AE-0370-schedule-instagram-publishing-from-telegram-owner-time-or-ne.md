# AE-0370 — Schedule Instagram publishing from Telegram (owner time or next good slot)

Status: In Development
Tier: T1
Priority: P1
Type: Bugfix
Area: backend
Owner: Claude Code (claude-opus-5-5)
Branch: fix/ae-0370-scheduled-publish
Created: 2026-10-15
Updated: 2026-10-15
Parent: AE-0348

## Goal

From the Telegram review, the owner publishes an approved carousel now, or schedules it for a
good slot or a time they type, and the worker publishes it at that time.

## Problem

Today Approve publishes at once, whatever the hour, so posts go out when the audience is
offline. The Instagram Graph API has no native scheduling (`media_publish` posts immediately,
there is no `scheduled_publish_time` for Instagram) and containers expire 24 h after creation,
so scheduling must be our own queue: store the time, create the containers when due.

## Scope

- Approve answers with `🚀 Publicar agora` (`ap:pubnow:<run>`) and `🗓 Agendar`
  (`ap:sched:<run>`); callback data ≤ 64 bytes. Publicar agora keeps today's path.
- Agendar: next 3 of `12:00`, `18:00`, `21:00` America/Sao_Paulo, each ≥ 15 min ahead,
  rolling over to the next day; `✏️ Outro horário` → ForceReply for `HH:MM` or
  `DD/MM HH:MM`; past and > 30 days refused with a clear reply.
- Chosen time: approve final review (`approved_for_publish`), no release; CAS
  `awaiting_owner → scheduled` with `scheduled_at`; confirmation `🗓 Agendado para dd/mm HH:MM`
  with `🚀 Publicar agora` and `❌ Cancelar agendamento`.
- Worker tick: due run → `scheduled → publishing` (`schedule_due`), release, existing publish
  path (quota, containers, Story, notice). > 10 min late → notice says
  `(publicado com atraso de N min)`. Carousel no longer approved → `expired`
  (`schedule_withdrawn`).
- Cancel → `awaiting_owner` + review keyboard; Publicar agora while scheduled publishes now.
- `AUTOPILOT_DEFAULT_PUBLISH` = `now` | `next_slot` (default `now`) in settings,
  `backend/.env.example`, `deploy.yml`, `docker-compose.prod.yml`, and the env-parity gate.
- State machine: `scheduled` with `awaiting_owner→scheduled`, `scheduled→publishing`,
  `scheduled→awaiting_owner`, `scheduled→expired`.
- One additive Alembic migration (`a9b0c1d2e3f4`): `autopilot_runs.scheduled_at` TIMESTAMPTZ
  NULL + index `(state, scheduled_at)`.

## Non-Goals

- Do not refactor unrelated code.
- Editing a schedule in place (cancel, then schedule again).
- Scheduling from the web UI.
- Per-niche or learned slot times.

## Acceptance Criteria

- [x] Approve shows the two buttons; Publicar agora approves, releases and publishes as before.
- [x] Agendar lists 3 slots (≥ 15 min, rollover, America/Sao_Paulo) + Outro horário.
- [x] Typed `HH:MM` / `DD/MM HH:MM` parsed; invalid, past and > 30 days refused and re-asked.
- [x] Chosen time → `scheduled` with `scheduled_at`, workflow approved, carousel still private.
- [x] Double tap schedules once; non-owner taps change nothing.
- [x] Due tick publishes once (claims + `ig_post_id`), with the Story; late > 10 min says so.
- [x] Cancel → `awaiting_owner` + review keyboard; Publicar agora while scheduled publishes.
- [x] 72 h review expiry never expires a `scheduled` run; withdrawn carousel → `expired`.
- [x] `next_slot` mode schedules the next slot on Approve.
- [x] Real-engine integration: schedule → due tick → published + Story.
- [x] Gherkin: `backend/tests/features/autopilot_scheduled_publish.feature`.
- [ ] DB gates (test, diff-cover, migrations, schema-drift) and the Python 3.11 import check,
  relayed from the x86 orchestrator.

## Repro Steps

1. An autopilot carousel reaches final review; the owner taps Approve on Telegram.
2. Before: it publishes at once.
3. After: the owner picks Publicar agora or Agendar; a scheduled run publishes at its time.

## Affected Areas

- [x] Backend
- [ ] Frontend
- [x] Tests

## Dependencies

AE-0369 (merged). **Migration `a9b0c1d2e3f4` must be applied by hand on prod** (prod deploys do
not run Alembic); the SQL is in `.agent/reports/AE-0370.dev-summary.md`. AE-0367 (not merged
yet) also edits `owner_actions.py` / `webhook_constants.py` / `OwnerActionDeps`; expect small
textual merge conflicts there (both sides keep their additions).

## Progress Log

### 2026-10-15

Ticket created from the owner brief (hotfix fast path, behaviour change → Gherkin first).
Implemented on the Pi; static gates and targeted tests run here; DB gates relayed to x86.

## Files Touched

- `backend/alembic/versions/a9b0c1d2e3f4_autopilot_run_scheduled_at.py` (new)
- `backend/src/rag_backend/modules/autopilot/schedule_constants.py` (new)
- `backend/src/rag_backend/modules/autopilot/domain/{schedule,schedule_keyboards,schedule_ports}.py` (new)
- `backend/src/rag_backend/modules/autopilot/application/{publish_choice,owner_approval,owner_replies,schedule_steps,scheduled_publish}.py` (new)
- `backend/src/rag_backend/modules/autopilot/infrastructure/schedule_store.py`, `bootstrap_schedule.py` (new)
- `backend/src/rag_backend/modules/autopilot/application/{owner_actions,publish_job}.py`
- `backend/src/rag_backend/modules/autopilot/domain/{models,state_machine,callback_parse,messages,owner_ports,publish,published_copy}.py`
- `backend/src/rag_backend/modules/autopilot/infrastructure/{models,repository,run_mapping,telegram_reply}.py`
- `backend/src/rag_backend/modules/autopilot/{bootstrap,bootstrap_webhook}.py`
- `backend/src/rag_backend/infrastructure/config/settings.py`, `backend/.env.example`
- `.github/workflows/deploy.yml`, `docker-compose.prod.yml`, `scripts/ci/check_autopilot_env_parity.py`
- `backend/tests/features/autopilot_scheduled_publish.feature` (new), `autopilot_owner_actions.feature`
- `backend/tests/unit/modules/autopilot/test_schedule_{domain,webhook,cancel,persistence}_ae0370.py`,
  `test_scheduled_publish_ae0370.py` (new); `test_owner_actions.py`, `test_state_machine.py`
- `backend/tests/integration/test_autopilot_scheduled_publish.py` (new),
  `test_autopilot_owner_actions.py`, `test_autopilot_migration.py`
- `backend/tests/unit/scripts_ci/test_check_autopilot_env_parity.py`
- `docs/architecture/grokbot-autopilot.md`

## Test Evidence

See `.agent/reports/AE-0370.dev-summary.md`.

## QA Report

Pending.

## Blockers

None.
