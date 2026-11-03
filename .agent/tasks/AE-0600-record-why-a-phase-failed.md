# AE-0600 — Record why a carousel phase failed instead of losing it

Status: In Development
Tier: T1
Priority: High
Type: Bugfix
Area: Backend
Owner: Pedro Marins
Agent Lane: developer → qa → release
Branch: fix/ae-0600-outline-failure-cause
Kanban Card: TBD
Created: 2026-11-03
Updated: 2026-11-03

## Goal

When a background resume fails, the carousel row, the `workflow_failed` generation
event and the generation run all say why (error class + a short safe code), so a
failure can be triaged from the database instead of from container logs that are
gone. Fix the bug that most likely produced the two prod failures.

## Problem

Prod triage 2026-11-02 (read-only): two autopilot POV carousels (`84a58b72`,
`74d35153`) failed 11 and 17 minutes into their run:

- carousel `current_phase=outline`, `phase_status=failed`, `error_message` empty;
- generation event `workflow_failed`, `error_code=resume_validation_failed`,
  `error_type=ValueError`;
- autopilot run `escalated` / `phase_failed`;
- their `generation_runs` rows say `succeeded`.

The exception text was only in container logs, which are gone.

## Findings (step 1, read before coding)

1. **The `phase` on the event is the phase the resume started from, not the phase
   that failed.** `editorial_workflow_resume_runner._run_background_resume` records
   `phase=prior_phase` (the gate being resumed), and the carousel row keeps the
   last synced `current_phase` because the failing node never synced. So
   `outline` + `failed` means "the resume from the outline gate failed": the
   outline was already generated and approved, and the node that raised is the
   **content** phase that runs next (slide drafts, persona scoring, EN
   translation, caption, LinkedIn). That matches 11-17 minutes in.
2. **The outline call itself is not the cause.** `PovOutlineMixin.generate_pov_outline`
   goes through `ainvoke_json`, which retries 5× per model (re-roll on empty,
   repair on malformed) and then re-issues the call on the fallback
   (`fallback_runnable_for`). Prod's reasoning queue is
   `go:deepseek-v4-pro,go:qwen3.8-max` (deploy.yml default), and
   `ModelQueueChatModel.as_fallback()` returns `[qwen3.8-max]`, so the fallback
   **is** tried for the outline. The slide drafter also goes through
   `ainvoke_json`.
3. **Bug found: the EN slide translation has no JSON retry and no fallback.**
   `editorial_distribution_generation._generate_en_translations` (content phase,
   via `build_editorial_distribution_updates`) makes a single `llm.ainvoke` and
   raises `ValueError(en_translation_parse_failed)` on the first malformed or
   truncated answer. The routed/queue models only fall back on errors, timeouts
   and empty answers, never on bad JSON, and nothing between the node and the
   runner catches it. It is the one JSON-parsing LLM call of the content phase
   that does not use the shared retry policy, and its payload (every slide with
   its long-form notes) is the largest, so truncation is most likely there. This
   is the most probable cause of both failures.
4. **Why the cause was lost.** The runner's `except ValueError` maps the message to
   a client-safe SSE message (only 5 known codes, else `background_resume_failed`),
   logs the detail only for 2 codes, sets `phase_status=failed` without
   `error_message`, and records `workflow_failed` with only the error class.
5. **Why the run says `succeeded`.** The runner swallows the exception (by design:
   it already marked the row failed and published `run.finished(failed)`), so the
   queue executor returns `DONE` and `GenerationJobHandler._settle` marks the run
   `succeeded` unconditionally.

Not proven: the container logs are gone, Langfuse is not reachable from this
worktree (no keys in the environment or in a `.env`), and the optional read-only
prod check was skipped because the prod host key is not in this machine's
`known_hosts` (not trusted blindly). Other `ValueError`s are possible on the same
path (`persona_score_too_low`, `invalid JSON` from a slide draft after the
fallback, `presentation_validation_blocked`); the visibility fix below names
whichever one happens next.

## Scope

- EN slide translation goes through `ainvoke_json` (re-roll, repair, 5 attempts
  per model, then the fallback model), still Langfuse-traced, still raising
  `ValueError(en_translation_parse_failed)` when everything is exhausted.
- A safe failure cause `<ErrorClass>: <code>`: the code is the exception message
  when it is a snake_case error code, a mapped code for the few sentence-style
  error constants of the pipeline, else `unclassified`. Never the raw message.
- The background resume stores that cause on `carousel_projects.error_message`
  when it marks the project failed (ValueError, other exception, cancellation).
- The `workflow_failed` event carries `error_type` (class) and `reason` (code).
- A generation run whose drive ended after a workflow failure is moved to the
  existing `dead_letter` status with `last_error_code=workflow_failed` and
  `last_error=<cause>`, instead of `succeeded`.

## Non-Goals

- No new run status, no new event detail key, no migration.
- No prompt change, no validation/gate/threshold change.
- No change to the SSE messages the browser sees.

## Acceptance Criteria

- [ ] A malformed EN translation answer is retried/repaired and then re-issued on
      the fallback model before `en_translation_parse_failed` is raised.
- [ ] A ValueError during a background resume stores
      `error_message="ValueError: <code>"` on the carousel row.
- [ ] The `workflow_failed` event records `details.error_type` and
      `details.reason=<code>`; a free-text message never reaches the row or event.
- [ ] A generation run whose workflow failed ends `dead_letter`
      (`last_error_code=workflow_failed`, `last_error=<cause>`), records
      `run_dead_letter`, and does not stage a second owner notice.
- [ ] A later successful workflow outcome in the same drive still ends `succeeded`.

## Gherkin Scenarios

See `backend/tests/features/phase_failure_cause_ae0600.feature`.

## Affected Areas

- Backend: resume runner + failure marking, write owner, generation queue handler
  and event scope, EN translation.
- Database: none (existing columns `error_message`, `last_error_code`, `last_error`).
- Prompts/LLM: none changed; translation now uses the shared JSON retry policy.
- Observability: richer `workflow_failed` details, run `last_error`.

## Dependencies

- Related: AE-0391/AE-0395 (fallback model), AE-0399 (model queue).

## Implementation Plan

1. Feature file, failing tests.
2. Failure cause helper; runner + failure marking + write owner.
3. Event reason + run-scoped failure note; handler dead-letters on it.
4. EN translation through `ainvoke_json`.
5. Full backend gates.

## QA Checklist

- [ ] Security reviewed (no user content in row/event/run)
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-11-03

Ticket created from the worker brief; findings above.

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Decision Log

- **Run status for a failed workflow = existing `dead_letter`.** It is the only
  failed terminal status in the vocabulary. It is set by the job handler when the
  drive returns `DONE` after the resume runner noted a failure in the run's event
  scope. Unlike the handler's own dead-letter path it does **not** call
  `DeadLetterNotices.stage`: the runner already marked the project failed and
  published `run.finished(failed)`, and the autopilot already escalated, so a
  second park/notice would be a duplicate. The dead-letter revive scan only
  revives autopilot runs parked with a `queue_dead_letter:*` reason, so an
  autopilot run escalated as `phase_failed` is not auto-retried by this change.
- **A later successful workflow outcome in the same drive clears the note** (last
  outcome wins). The `background_resume_stuck` path (row reverted to
  `awaiting_human`) and the stale-epoch warning do not note a failure.
- **Cause code rule.** A message that is a lowercase snake_case code (≤64 chars)
  is kept; a few sentence-style constants map to codes (`invalid_json`,
  `artifact_staging_incomplete`, `translations_required`); anything else is
  `unclassified`. Pydantic `ValidationError` (a `ValueError`) and formatted
  messages therefore never leak input values.
- **`error_message` keeps the last failure cause**; `phase_status` says whether it
  is current. Clearing it on the next success is out of scope.
- **The event keeps `error_code=resume_validation_failed`** (dashboards group on
  it) and adds the specific code under the existing allowed detail key `reason`.
- **Prod read skipped**: host key unknown on this machine; not trusted blindly.

## Blockers

None.

## Final Summary

Pending.
