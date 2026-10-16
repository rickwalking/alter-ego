# AE-0404 — Telegram schedule picker (day, then time) with recommended slots from audience and post data

Status: In Development
Tier: T1
Priority: P0
Type: Bug
Area: backend
Owner: Claude (owner-reported hotfix)
Agent Lane: developer → qa → release
Branch: fix/ae-0404-schedule-picker-recommended
Kanban Card: TBD
Created: 2026-10-16
Updated: 2026-10-16

## Goal

From Telegram, the owner picks the publish day and then the time, from recommended slots that come from the audience and our post data. An auto-scheduled run can be moved the same way.

## Problem

Owner report (2026-10-16, prod run b241ded5): "Schedule on Telegram does not allow me to select day and time. Also, it should recommend best times and days based on previous posts."

With `AUTOPILOT_DEFAULT_PUBLISH=next_slot`, Approve scheduled the run straight away ("🗓 Agendado para 20/10 12:00 (próximo horário bom)"). The message only offered `🚀 Publicar agora` and `❌ Cancelar agendamento`. The AE-0370 slot menu (3 fixed slots and a typed time) appeared only in `now` mode. No slot used the audience or our post data.

## Scope

- **Reaching the picker:** every scheduled message gets `🗓 Mudar dia/horário` (`ap:sched:`). The review keyboard gets `🗓 Agendar` on a second row. Both open the picker.
- **Step 1, the day:** 7 São Paulo days, from today (when a slot is still ≥15 min ahead) or from tomorrow. Labels look like `Ter 20/10 ⭐`, 3 per row. Callback `ap:d:<yyyymmdd>:<run>` (50 bytes).
- **Step 2, the time:** the day's top 4 whole-hour times (the best one starred), with each reason in the message text. Then `✏️ Outro horário` and `← Dias` (`ap:days:<run>`). Slots respect `SCHEDULE_MIN_LEAD_MINUTES` and `SCHEDULE_MAX_AHEAD_DAYS`.
- **Confirming:** an `awaiting_owner` run is scheduled (the AE-0370 path). A `scheduled` run moves `scheduled → scheduled` with the new `scheduled_at`: a new state-machine edge, reason `owner_rescheduled`, compare-and-set. The message reads `🗓 Agendado para Qua 21/10 18:00 (motivo)` and keeps the 3 buttons. A typed `Outro horário` also reschedules a scheduled run.
- **Recommender** (`domain/recommend.py`, pure): scores each São Paulo (day, hour) slot by blending three signals.
  - **audience:** `online_followers` per UTC hour, min-max normalised.
  - **performance:** `(saved + shares + total_interactions) / reach` per (weekday, hour) bucket, shrunk by `n/(n+5)`.
  - **prior:** POV Tue/Thu 12:00 (1.0), with 12/18/21 at 0.5 for POV; Radar 12/18/21 (1.0).
  - The weights live in `recommend_constants.py`.
  - The auto `next_slot` picks the best slot of the 7 days. POV runs and Radar runs with no data behave as before.
- **Signals** (`infrastructure/schedule_signals.py`, `audience_gateway.py`):
  - Graph `/{ig-user-id}/insights?metric=online_followers&period=lifetime`, cached in the new `instagram_audience_hours` table and read at most once a day.
  - A failure is logged; the cache (or nothing) is used, and the attempt is recorded so it is not retried for a day.
  - The cache write happens in a savepoint, so a concurrent insert never fails the webhook.
  - Posts are read from `instagram_post_insights` joined to runs (`scheduled_at`, else `updated_at`) and to manual publishes (`claimed_at`).
- **Migration:** additive and idempotent `a0e4f0a4b4c4` (`instagram_audience_hours`).

## Non-Goals

- Story step, late-publish notice, due sweep, publish-now and cancel logic are unchanged (only the keyboard row layout of a scheduled message changes).
- No prompt or LLM change.

## Acceptance Criteria

- [x] AC1: An auto-scheduled message shows `🚀 Publicar agora`, `🗓 Mudar dia/horário`, `❌ Cancelar agendamento`; the review keyboard shows `🗓 Agendar`; both open the day step.
- [x] AC2: The day step lists 7 days (today or tomorrow first) with the best days starred, 3 per row.
- [x] AC3: The time step lists the top 4 times with reasons in the text, plus `✏️ Outro horário` and `← Dias`.
- [x] AC4: Confirming schedules an awaiting run or reschedules a scheduled run (CAS, idempotent) and edits the message with the reason and the 3 buttons.
- [x] AC5: A past slot, one beyond 30 days, or a day outside the window is refused and the day step is shown again.
- [x] AC6: Every picker callback is ≤64 bytes; malformed ones are not parsed.
- [x] AC7: With no insights the POV prior (Tue/Thu 12:00) wins; Radar keeps 12/18/21.
- [x] AC8: With `online_followers`, the peak hour ranks first; post performance shifts the ranking with shrinkage.
- [x] AC9: An insights fetch error falls back silently (logged) and is not retried for a day.
- [x] AC10: Publish now, cancel, typed time, the due sweep, the Story step and the late notice still pass their AE-0369/AE-0370 tests.

## Gherkin Scenarios

`backend/tests/features/telegram_schedule_picker_ae0404.feature`

## Delta

### ADDED

- `backend/src/rag_backend/modules/autopilot/recommend_constants.py`
- `backend/src/rag_backend/modules/autopilot/domain/recommend.py`
- `backend/src/rag_backend/modules/autopilot/application/schedule_picker.py`
- `backend/src/rag_backend/modules/autopilot/infrastructure/audience_gateway.py`
- `backend/src/rag_backend/modules/autopilot/infrastructure/schedule_signals.py`
- `backend/alembic/versions/a0e4f0a4b4c4_instagram_audience_hours.py`
- `backend/tests/features/telegram_schedule_picker_ae0404.feature`
- `backend/tests/unit/modules/autopilot/test_schedule_recommend_ae0404.py`
- `backend/tests/unit/modules/autopilot/test_schedule_picker_ae0404.py`
- `backend/tests/integration/test_schedule_signals_ae0404.py`
- `backend/tests/integration/test_audience_hours_migration_ae0404.py`

### MODIFIED

- `schedule_constants.py`, `domain/schedule.py`, `domain/schedule_keyboards.py`, `domain/callback_parse.py`, `domain/schedule_ports.py`, `domain/state_machine.py`, `domain/messages.py` (review keyboard), `domain/pov_schedule.py`
- `application/publish_choice.py`, `application/owner_actions.py`, `bootstrap_webhook.py`, `public.py`, `infrastructure/insights_models.py`
- AE-0370/0377/0367 tests updated for the intended keyboard and label changes; migration head tests now point to `a0e4f0a4b4c4`.
- `docs/architecture/grokbot-autopilot.md`, `docs/architecture/instagram-growth-pov-mode.md`

### REMOVED

- `next_slots`, `slot_label`, `local_label`, `slot_keyboard`/`SlotMenu`, `PovPublishSlots`, `slot_policy_for`, `publish_slots_for` (replaced by the recommender), and their now-unused constants.

## Affected Areas

- Backend: autopilot Telegram scheduling
- Frontend: none
- Database: new table `instagram_audience_hours` (additive)
- API: Telegram callback data (`ap:d:`, `ap:days:`)
- Tests: unit + integration + feature
- Docs: architecture sections
- Prompts/LLM: none
- Observability: `autopilot_audience_fetch_failed`, `autopilot_audience_save_failed` logs
- Deployment: migration `a0e4f0a4b4c4` (also created at startup like the other autopilot tables)

## Dependencies

- Blocks: none
- Blocked by: none
- Related: AE-0370, AE-0371/AE-0378 (insights), AE-0377 (POV slots)

## Implementation Plan

1. Pure recommender and keyboards.
2. Picker handlers and the reschedule edge.
3. Audience gateway, daily cache and post engagement.
4. Tests, feature, docs.

## QA Checklist

- [x] Security reviewed (owner allowlist unchanged; callbacks are regex-allowlisted and the date is validated; Graph token not logged)
- [x] Code quality reviewed
- [x] Acceptance criteria validated
- [x] Edge cases tested (stale day, past/too-far slot, lost CAS race, concurrent cache write, Graph error, no account)
- [x] Orphan/unfinished code checked (replaced slot helpers removed)

## Progress Log

### 2026-10-16

Reproduced from the prod report and code. Built the picker and recommender. Gates run one at a time (hotfix fast path).

## Files Touched

See Delta.

## Test Evidence

See `.agent/reports/AE-0404.dev-summary.md`.

## QA Report

Pending (hotfix fast path: CI Test & Coverage decides).

## Decision Log

- 2026-10-16: **Reschedule is a `scheduled → scheduled` CAS** (new edge), not cancel-and-schedule. Cancel-and-schedule would run the editorial approve again and briefly reopen the review. The due tick's CAS and this one exclude each other.
- 2026-10-16: **`🗓 Mudar dia/horário` reuses `ap:sched:`**, and `🗓 Agendar` is added to the review keyboard as its own second row. This keeps the first row at Approve/Rework/Reject (+Fix).
- 2026-10-16: **Weights:** prior 0.3, audience 0.4, performance 0.5 with `n/(n+5)` shrinkage.
  - Audience alone outranks the prior.
  - 3 posts in a bucket give 0.19, below the prior's 0.3. Performance needs about 8 posts in a bucket before it can beat the prior.
  - POV with no data keeps Tue/Thu 12:00. With audience data, a POV run may move to a peak hour; that is intended ("strong default when there's no data").
- 2026-10-16: **Candidate times are whole hours from 08:00 to 22:00 São Paulo.**
  - Ties break by the distance to a default slot, then by time. Without data, the 4th Radar time is therefore 11:00 ("horário alternativo").
  - Days are starred only when they differ, with at most 3 starred, each within 95% of the best day.
- 2026-10-16: **Audience is summed over the days Graph returns, per UTC hour**, and converted per slot (DST-safe). The table stores `checked_at` (last attempt) and `fetched_at` (last success), so a refused or deprecated metric costs one Graph call a day, not one per tap.
- 2026-10-16: **A typed `Outro horário` time is confirmed without a reason.** A reason only describes recommended slots.
- 2026-10-16: **The audience row is written in a savepoint inside the webhook transaction.** A concurrent insert is logged, never raised, so it cannot roll back the owner's tap.
- 2026-10-16: **Migration `a0e4f0a4b4c4` chains on `d3e4f5a6b7c8`.** Parallel hotfixes (AE-0401/AE-0403) that also add a revision on that head need a rebase of `down_revision` at merge.

## Blockers

None.

## Final Summary

Pending.
