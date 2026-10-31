# AE-0523 — P2 — Telegram queue position, Aprovar todas, dead-letter Retry/Discard, over-cap backlog

Status: Done
Tier: T2
Priority: Medium
Type: Feature
Area: Backend
Owner: Claude Code (claude-opus-5-5)
Agent Lane: developer → qa → release
Branch: feat/ae-0523-telegram-queue-flow
Kanban Card: TBD
Created: 2026-10-22
Updated: 2026-10-24

## Goal

Make the queue visible and controllable from Telegram, per the AE-0517 plan §4.5 and Pedro's decisions (concurrency 1, strict FIFO, over-cap themes roll to the next day and can be triggered manually).

## Problem

Phase of AE-0517 (carousel generation queue). Plan: `.agent/reports/AE-0517.arch-plan.md`; decision:
`docs/decisions/0026-carousel-generation-queue.md` (provisional until the AE-0520 exit criteria hold); skeptical review:
`.agent/reports/AE-0517.skeptical-review.md`. Order: AE-0520 → AE-0521 → validation on the
disposable droplet → AE-0522 (live on merge) → AE-0523, AE-0524, AE-0525, AE-0526.

## Scope

- Confirmar (and the edited-thesis reply) shows "Na fila: posição N de M — início estimado HH:MM": position from the
  generation queue's FIFO order (active generation runs, then driven autopilot runs not picked up yet), start from
  the average of the last 10 finished autopilot drives (15 min without history), São Paulo time.
- "Aprovar todas": one summary when two or more POV runs whose prompts went out wait for their thesis; one tap
  confirms each (its own compare-and-set) and lists every thesis with its position; a thesis without a draft is
  named for "Editar".
- Dead letter: the escalated/failed notice of a run the queue parked (`queue_dead_letter:<code>`) explains the code
  (budget codes mention a possible memory limit while rendering) and carries "Tentar de novo" / "Descartar".
  Retry of an escalated run → `generating` (resumes from its checkpoint) and requeues its dead-lettered generation
  run in the same transaction (failing phase reset); retry of a failed run (died before it started; `failed` stays
  terminal) queues a new run for the theme. Discard → `rejected` (or marks the failed run discarded).
- Backlog: themes the daily cap left out are kept (best score first) until 10 wait; more are refused as
  `backlog_full`; Radar IA (news) topics never wait. The next scout batch gives the day's free slots to backlog
  themes from earlier days, oldest first. Themes are announced once with a "Gerar agora" button each; a theme older
  than 7 days expires with one note. "Gerar agora" queues the theme at the end of the queue, outside the daily cap.

## Non-Goals

- Changing the daily cap's meaning or the concurrency (Pedro: 1). The dashboard queue panel (AE-0526). The 04:00
  recovery scan (AE-0524).

## Acceptance Criteria

- [ ] AC1 Given three theses arrive, When Pedro taps "Aprovar todas", Then three runs are queued in FIFO order and the
  summary shows each one's position and estimated start; a single Confirmar shows its position too.
- [ ] AC2 Given a run is dead-lettered, Then Pedro receives one message with the reason and "Tentar de novo" /
  "Descartar"; Retry re-queues it once (escalated: resumes from the checkpoint; failed: a new run), Discard closes it,
  and an escalation that is not a queue dead letter cannot be retried this way.
- [ ] AC3 Given more themes than the daily cap, Then the extra themes (up to 10 waiting) are queued the next morning
  before new ones, are announced once with "Gerar agora", and expire after 7 days with one note.
- [ ] AC5 Given waiting themes and no scout batch, When 08:05 São Paulo time comes, Then they are queued into the free
  slots once.
- [ ] AC4 Given "Gerar agora", Then the theme is queued at once at the end of the queue and does not count toward the
  daily cap; a second tap queues nothing.

## Gherkin

`backend/tests/features/telegram_queue_flow_ae0523.feature`.

## Decision Log

- 2026-10-22: Created from the AE-0517 plan after three skeptical review rounds (Pedro's cap).
- 2026-10-24 (Pedro: no feature flags, strict FIFO, concurrency 1): no schema change; backlog states live in the
  topic candidate's free-text status. `failed` stays terminal (state-machine spec), so a retry of a run that failed
  before it started is a new run for the same theme; the one new edge is `escalated → generating` (owner retry of a
  queue dead letter). A retried run counts toward the day it is created; "Gerar agora" runs do not count.
  Out-of-memory kills are not reported by the worker as such; the budget-exhausted texts name memory as a likely
  cause.
- 2026-10-24 (review): "Aprovar todas" confirms only the theses a summary listed; a requeued dead letter goes to
  the back of the queue and the dispatcher mirrors a held job only onto the row still pointing at it; backlog status
  moves are compare-and-set. Known limit: a run parked while applying a rework loses that rework's feedback (the
  recovery clears it when parking); after "Tentar de novo" Pedro asks for the change again at the review.
- 2026-10-24 (Pedro, #281 review): daily cap 3; backlog expiry 7 days with a notice and limit 10 kept; the rollover
  gets its own daily promotion at 08:05 São Paulo time in the worker. The prod deploy reads the
  `AUTOPILOT_DAILY_CAP` GitHub secret first, so the secret must be set to 3 (or removed) for prod to use 3.

## Final Summary

Merged to `main` in PR #281 (3bbbd6d6, 2026-10-25). The status was left open after the merge; closed on 2026-10-30 (ticket housekeeping, no code change).
