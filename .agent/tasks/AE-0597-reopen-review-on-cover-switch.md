# AE-0597 — A cover switch reopens the final review of an approved or scheduled carousel

Status: In Development
Tier: T2
Priority: High
Type: Feature
Area: Backend
Owner: Pedro Marins
Agent Lane: developer → qa → release
Branch: feat/ae-0597-reopen-review
Kanban Card: TBD
Created: 2026-11-02
Updated: 2026-11-02

## Goal

Pedro's decision (2026-11-02): AE-0594 refuses a slide-1 cover switch on an
approved, scheduled or published carousel. This ticket lifts the refusal for
approved and scheduled carousels. A cover switch (website picker
`PUT /cover`, the website auto-switch after a "Gerar capa com Grok"
success, the GrokBot cover on Telegram, `PUT /hook-photo`) on such a
carousel drops the approval in the same transaction as the slide-1 write and
the needs-republish marker. The carousel goes back to
`final_review / awaiting_human` (draft), is rendered again, and only a fresh
approve restores `approved_for_publish`. Published (released or public)
carousels never change: they keep the AE-0594 refusal.

## Problem

AE-0594 left the guard easy to lift (`cover_switch_guard.py`) but had no way
to revoke a final-review approval: the graph parks an approved carousel at
`approved_hold`, which routes only to END or to a full re-run of a phase, and
the publish paths (website release, Instagram, the autopilot publish gate, the
scheduled sweep) only look at `workflow_status`. The scheduled sweep also read
the approval without a lock, and the release (`release_public`) retried past a
lock-version move without re-checking the approval, so a switch that landed
between the sweep's read and its release could have been released with an
unreviewed cover.

## Findings

- **Missed slot (the existing scheduler behaviour): expire, never roll
  forward.** `ScheduledPublishSweep._fire`
  (`backend/src/rag_backend/modules/autopilot/application/scheduled_publish.py:85-89`)
  moves a due `scheduled` run whose carousel is no longer
  `approved_for_publish` to `expired` (reason `schedule_withdrawn`, owner text
  `TEXT_SCHEDULE_WITHDRAWN`: "Agendamento expirado: o carrossel não está mais
  aprovado. Nada foi publicado."). A due run that is still approved is
  published late (`late_minutes`), never moved to another slot. This ticket
  follows it: a reopened run whose kept time passes before it is approved
  again expires the same way.
- `update_from_entity` (used by `update_project`) writes `current_phase` and
  `phase_status` from the entity, and `update_project` commits. The switch
  service therefore stages the marker and the reopen on the same session
  before `update_project`, and puts the reopened phase on the entity, so one
  commit carries the lock-version bump, slide 1, the marker and the dropped
  approval.
- The GrokBot rework (`ReworkStep._cover`) only ran at
  `final_review / awaiting_human`, so it could never meet an approved
  carousel. The only approved case it can meet is a cancelled schedule (run
  `awaiting_owner`, carousel approved); it now runs there too.

## Pedro's decision (2026-11-02)

1. A cover switch on an approved or scheduled carousel drops the approval
   atomically with the slide-1 write and the marker; the carousel is back in
   final review, awaiting human; it re-renders; a fresh approve restores it.
2. Published carousels never change (AE-0594 refusal kept).
3. A reopened scheduled autopilot carousel keeps its scheduled time and waits;
   if the slot passes while it waits it must not publish (follow the existing
   missed-slot behaviour: expire).
4. The Telegram review is re-sent through the AE-0594 path; the API layer
   composes the autopilot hook (the #330 pattern); editorial never imports
   autopilot.
5. A Postgres test races the switch against the scheduled-publish sweep.

## Decisions taken during development

- **Graph:** a new resume action `reopen_review` on the `approved_hold`
  interrupt sets `workflow_status = draft`, `quality_passed = false`,
  `phase_status = awaiting_human` and routes to the `final_review` node, which
  interrupts again (no LLM call, no phase re-run). A later approve goes through
  the normal `final_review` approve and parks at `approved_hold` again.
- **Order of the two stores:** the checkpoint is reopened first, then the
  row (the publish lock) is written and committed. A crash in between leaves
  the checkpoint asking for a review of a carousel still approved with its old
  cover, which is harmless (an approve re-approves it). The other order could
  leave an approval-dropped row whose checkpoint still says approved.
- **The kept time:** a reopened `scheduled` run moves `scheduled → reworking`
  (a new allowed transition, reason `cover_review_reopened`) and keeps
  `scheduled_at` (`clears_schedule` exempts that reason). The worker's normal
  final-review stop moves it to `awaiting_owner` and sends the review at the
  new lock version (the AE-0594 path). Approving that review approves the
  final review first, then schedules the run again at the kept time. If the
  kept time has passed, the approve expires the run (`schedule_withdrawn`)
  instead of approving anything.
- **The due sweep** also handles an `awaiting_owner` run with a kept time:
  at its time it expires (`schedule_withdrawn`) unless the carousel was
  approved again (on the website), in which case it is published as the
  scheduled run would have been. A run outside `scheduled` only keeps
  `scheduled_at` after a reopen, so no other run is picked up.
- **Locks:** the sweep locks the carousel row (`SELECT ... FOR UPDATE`) before
  it reads the approval and keeps the lock until it commits the run move and
  the release. Every switch writes under the lock-version CAS on the same row,
  so the two serialize. The release itself also requires
  `workflow_status = approved_for_publish` in its UPDATE (and reads it), so a
  `Publicar agora`, an approve's release or a website release can never make a
  reopened carousel public; it answers `version_conflict` like a moved version.
- **Rollback:** a rolled-back switch (failed render) restores the old cover
  but the approval stays dropped: the owner approves again. Approval is never
  restored automatically.
- **Hook photo:** the reopen is staged with the marker (the existing first
  commit), before the photo is written; the entity the route writes carries
  the reopened phase, so the later `update_project` does not undo it.
- **Telegram for the picker and the hook photo:** the routes call the
  autopilot `reopened` hook after their write: a `scheduled` or
  `awaiting_owner` run goes to `reworking` (anchor kept), and the worker sends
  the review again. The website auto-switch keeps the AE-0594 hold for an
  `awaiting_owner` run and calls the same hook for a scheduled one.

## Scope

- `cover_switch_guard.py`: `reopen_refusal` (published only) and
  `reopens_review` (approved, not public); `cover_switch_refusal` keeps its
  meaning for the render guard.
- Editorial: `CarouselProjectWriteOwner.reopen_final_review`, the
  `ApprovalReopen` adapter (checkpoint first, then the row) and the
  checkpoint reopener (`CarouselWorkflowEngine.reopen_final_review`).
- The four switch paths reopen instead of refusing an approved carousel.
- Autopilot: the `reopened` hook, the `(scheduled, reworking)` transition,
  the kept time on approve, the due sweep's row lock and kept-time runs.
- Publishing: the release requires the approval.
- Frontend: the picker's refusal text says "published" only (pt/en).

## Non-Goals

- No change for published carousels.
- No new database column or migration.
- No automatic re-approval and no roll-forward of a missed slot.

## Acceptance Criteria

- [ ] A cover switch on an approved (or scheduled) carousel, by each of the
      four paths, leaves the carousel `draft`, `final_review /
      awaiting_human`, with the new slide 1 and the marker, in one commit; the
      checkpoint waits at the final review again; the slides re-render.
- [ ] A fresh approve after the render restores `approved_for_publish`.
- [ ] A published carousel is still refused with
      `cover_switch_requires_review`; nothing is written or rendered.
- [ ] A reopened scheduled run keeps its time, gets a new Telegram review,
      and an approve schedules it again at that time; a passed time expires
      it (`schedule_withdrawn`) and nothing is published.
- [ ] Postgres race: the switch and the due sweep with real sessions and
      locks; either the release wins and the switch is refused as published,
      or the switch wins and nothing is released.
- [ ] The release refuses a carousel whose approval was dropped.
- [ ] Gates green (every backend gate except local mutation; frontend scope).

## Gherkin Scenarios

See `backend/tests/features/reopen_review_on_cover_switch_ae0597.feature`.

## Affected Areas

- Backend: editorial, autopilot, publishing, carousel services, routes
- Frontend: picker refusal text (pt/en)
- Database: none
- API: none (same status codes)
- Tests: unit, Postgres integration

## Dependencies

- Blocked by: AE-0594 (PR #338)
- Related: AE-0590, AE-0581

## Progress Log

### 2026-11-02

Ticket written from Pedro's decision (2026-11-02); findings and decisions
recorded above.

## Test Evidence

Pending.

## QA Report

Pending.
