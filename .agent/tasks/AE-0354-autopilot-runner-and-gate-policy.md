# AE-0354 — AutopilotRunner: drive editorial workflow in-process, auto-approve gates, stop at final_review

Status: Ready
Tier: T2
Priority: Critical
Type: Feature
Area: backend
Owner: Grok (Cursor CLI, grok-4.7-high)
Agent Lane: developer → qa → release
Branch: feat/ae-0354-autopilot-runner-and-gate-policy
Kanban Card: TBD
Created: 2026-10-13
Updated: 2026-10-13
Parent: AE-0348

## Goal

A worker-loop step that takes queued runs, creates + starts the carousel workflow in-process, auto-approves research/outline/content/design/images only when deterministic checks pass, revises or escalates otherwise, and ALWAYS stops at `final_review`.

## Problem

The workflow has 6 `interrupt()` gates and no auto mode; driving it over HTTP hits the 60-min JWT, `lock_version` races and the ~100 s Cloudflare cap on the synchronous `workflow/start`.

## Scope

- Use ONLY the editorial facade (`rag_backend.modules.editorial.public`: `EditorialService`/`EditorialWorkflow`, `StartWorkflowCommand`, `PHASE_*`, `PHASE_STATUS_*`, `REVIEW_ACTION_APPROVE/REVISE`, `WorkflowStateView`). If an operation you need is not on the facade, add it to the facade in this ticket (do not import internals).
- Owner identity: runs act as the user `AUTOPILOT_OWNER_USER_ID` (setting); `reviewer_id` left unset so the owner can resume.
- Create project with: topic, audience, niche, `language=pt-BR`, `generate_images=True`, slides ≤10 total (Instagram API max).
- `AutopilotRunner.tick(db)` registered in `application/workers/workflow_workers.py` `_run_tick` AFTER the existing steps, guarded by `settings.autopilot_enabled`; processes at most 1 run per tick; holds no lock across ticks (state machine + `lock_version` CAS).
- Gate policy `domain/policy.py` (pure): research ≥3 sources with content; outline slide count == slides_config total; content persona score ≥70 (constant from persona module) AND no forbidden phrases; design `presentation_validation` has no blockers; images: all assets present and each JPEG 1080×1350.
- Check fails → `revise` with templated feedback (prompt text in `agents/prompts/autopilot/v1/revise_feedback.yaml`, loaded via `render_prompt`), max 2 per phase (constant) → then state `escalated` with reason.
- On `final_review` + `awaiting_human` → transition `generating → awaiting_owner` and emit `content.autopilot.ready_for_owner` (consumed by AE-0355).
- Phase `failed`, run reaped/stale, or 409 revision-cap → `escalated`/`failed` with reason. Workflow `start` provider errors (429/503) → leave `queued`, increment attempts, give up after 3 → `failed`.
- Langfuse metadata `content_type=carousel`, `agent_name=autopilot`, `phase`, `project_id` on every call path that triggers LLM work.

## Non-Goals

- Ever approving `final_review` (only the owner via AE-0356).
- Changing the editorial graph or gate semantics.

## Acceptance Criteria

- [ ] WHEN a queued run is ticked THE runner SHALL create and start the workflow without any HTTP call.
- [ ] WHEN a gate is awaiting_human and its policy check passes THE runner SHALL resume `approve` with the current `lock_version`.
- [ ] WHEN the content persona score is <70 THE runner SHALL resume `revise` (max 2) and then escalate — it SHALL never approve below 70.
- [ ] WHEN the workflow reaches final_review THE runner SHALL stop, set `awaiting_owner`, and emit `content.autopilot.ready_for_owner` exactly once.
- [ ] WHEN a test drives the runner through all gates THE runner SHALL NOT call approve on `final_review` (asserted).
- [ ] WHEN `lock_version` conflicts (409) THE runner SHALL re-read state on the next tick, not crash or double-resume.
- [ ] WHEN `autopilot_enabled=false` THE worker tick SHALL skip the runner entirely.

## Gherkin Scenarios

```gherkin
Feature: Autopilot runner

  Scenario: Clean run reaches the owner
    Given a queued autopilot run
    And every gate's policy check passes
    When the runner ticks until idle
    Then the run state is "awaiting_owner"
    And final_review was never approved by the runner
    And one "content.autopilot.ready_for_owner" event was emitted

  Scenario: Low persona score is revised then escalated
    Given the content gate persona score stays at 62
    When the runner ticks until idle
    Then the content gate was revised 2 times
    And the run state is "escalated" with reason "persona_score_below_threshold"

  Scenario: Version conflict is retried safely
    Given the resume call returns a lock_version conflict
    When the runner ticks twice
    Then exactly one approve is applied to that gate

  Scenario: Provider outage on start
    Given workflow start fails with 503 three times
    When the runner ticks three times
    Then the run state is "failed" with reason "start_failed"
```

## Delta

### ADDED

- `backend/src/rag_backend/modules/autopilot/application/runner.py`
- `backend/src/rag_backend/modules/autopilot/domain/policy.py`
- `agents/prompts/autopilot/v1/revise_feedback.yaml` + README
- `backend/tests/features/autopilot_runner.feature`

### MODIFIED

- `application/workers/workflow_workers.py` (one optional collaborator, keep 3-arg signatures)
- `bootstrap/app_factory.py` (wire runner)
- `modules/editorial/public.py` only if a needed op is missing
- settings: `autopilot_enabled`, `autopilot_owner_user_id`

### REMOVED

- None.

## Affected Areas

- Backend: runner + policy
- Prompts/LLM: revise feedback yaml
- Observability: Langfuse metadata
- Tests: fake editorial facade + integration

## Dependencies

- Blocks: AE-0355, AE-0356
- Blocked by: AE-0350, AE-0353
- Related: `agents/carousel_workflow_nodes.py` gates, AE-0315 tick ordering

## Implementation Plan

1. Feature first.
2. Pure policy functions + exhaustive unit tests (mutation target ≥70%).
3. Runner against a fake facade (state script per scenario).
4. Wire into worker tick after existing steps.
5. One integration test with real editorial service and mocked LLM/image providers.

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
- [ ] Assert-never-approve-final_review test present
- [ ] No imports of editorial internals (import-linter)

## Progress Log

### 2026-10-13 00:00

Ticket created from docs/architecture/grokbot-autopilot.md (ticket #5).

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
