# AE-0288 — final-review send-back to content actually regenerates (preserving images)

Status: Review
Tier: T2
Priority: P2
Type: Bugfix
Area: backend
Owner: Unassigned
Agent Lane: architect → developer → qa → release
Branch: fix/ae-0288-carousel-send-back-content-regen
Kanban Card: TBD
Created: 2026-06-30
Updated: 2026-06-30

## Goal

Make a final-review "send-back" (`revise` with
`structured_feedback.target_phase="content"`) actually re-run the content phase
and deliver the reviewer's note to it, even when the carousel has already been
approved for publish (LangGraph at END). Existing slide images must be preserved.

## Problem

On prod carousel `a2991a39-4fcd-4730-94b1-8e74f7563fbc` the content repeated across
slides 2-4. The carousel was `approved_for_publish` (graph at END). Sending it back
to `content` via the resume API did NOT regenerate content — it only bumped
`revision_count[final_review]`. Two compounding backend bugs:

1. **Feedback keyed by `current_phase`, not `target_phase`.** `persist_phase_feedback`
   (`editorial_workflow_feedback.py:31`) stores the note + `revision_count++` under
   `prior["current_phase"]` (= `final_review`). The content node only regenerates
   from `phase_feedback["content"]` (`phase_artifact_runner.py:231` →
   `_content_revision_notes`). So a send-back note never reaches content.
   `target_phase` is available in `resume_workflow` but is NOT forwarded through
   `ResumeContext`/`PhaseFeedbackPersistParams` to the persist call site.
2. **Approved/END graph won't re-enter an earlier node.** `engine.resume`
   (`carousel_workflow_engine.py:100`) only forces `Command(goto=...)` when
   `needs_gate_reopen` is true, which requires `phase_status == awaiting_human`
   (`carousel_workflow_graph.py:60`). A fully-approved carousel (graph at END,
   `phase_status=approved`) falls through to a no-op `Command(resume=payload)`.

The paused-at-final_review case (gate still `awaiting_human`) already routes to
content via `review_updates_from_response`; only the approved/END case is broken,
and the feedback-keying bug affects both.

Images are independent of slide text and reused via
`generation_key=sha256(model,style,rendered_prompt)`, where `rendered_prompt`
derives from the slide's persisted `image_prompt` — the LLM-emitted value when
present, else the OUTLINE-HEADING fallback (`editorial_distribution_slide.py:65-69`,
`image_prompt_package.py:56-66`). So a content re-run reuses each slide's image
**when its `image_prompt` is unchanged** (true for heading-driven prompts with an
unchanged heading); it is not a blanket guarantee. The `image_path=None` reset
during distribution-persist does NOT lose images — reuse is by generation-record
hash, independent of `image_path` (`nodes/images.py:520`
`reuse_recorded_generation`).

## Scope (architectural — final-review hold)

**Pivot (see Decision Log):** the original plan (engine `Command(goto=target)` to
re-enter an *already-ended* graph) was empirically proven unreliable — LangGraph
does not reliably re-enter a terminated thread (10 mechanisms tested; all either
no-op, auto-approve straight through to END, or leave the node scheduled-not-run).
Instead, the graph no longer terminates on final-review approval:

- `carousel_workflow_graph.py`: new internal `approved_hold` node. On final-review
  approval the graph routes to `approved_hold` (was `END`), which `interrupt()`s
  and **holds** — keeping the thread resumable. `route_after_hold` returns a
  send-back target → that phase, else → `END` (finalize).
- `carousel_workflow_nodes.py`: `approved_hold_phase` (holds at the interrupt).
- `domain/constants/carousel_workflow.py`: `PHASE_APPROVED_HOLD` (graph-only;
  never a user-facing phase).
- `carousel_workflow_engine.py` `get_state`: while parked at `approved_hold`,
  keep `current_phase=final_review` / `phase_status=approved` (do NOT surface the
  hold node or flip to awaiting_human) — the carousel stays publishable. This also
  prevents the spurious `review_required` SSE and the `_detect_resume_stuck`
  false-positive the held interrupt would otherwise cause.
- `editorial_workflow_feedback.py` / `_types.py` / `_service_helpers.py` /
  `_service.py`: a send-back keys feedback + revision_count under `target_phase`
  (not `current_phase`), and `mark_resume_in_progress` drops the DB publish lock
  synchronously when resuming an approved carousel (no stale-publish window).

## Non-Goals

- **Does not retroactively fix already-ended carousels** (e.g. prod `a2991a39`):
  their LangGraph thread is already terminated; the hold only applies to carousels
  created/approved after deploy. Those need a separate one-off.
- No change to image generation/reuse, the validator, or the budgets.
- No new HTTP endpoint; reuses `/workflow/resume`.

## Acceptance Criteria

- [ ] `persist_phase_feedback` with `target_phase="content"` while
      `current_phase="final_review"` appends the note to `phase_feedback["content"]`
      and increments `revision_count["content"]` (not `final_review`).
- [ ] `engine.resume` from an approved/END checkpoint, given
      `structured_feedback.target_phase="content"`, re-enters the content node
      (snapshot `next == ("content",)`), not a no-op at END.
- [ ] A send-back from final_review to content regenerates `slide_drafts` /
      `localized_slides` (content node runs with the new revision note).
- [ ] `image_assets` is unchanged across the send-back (images reused, not
      regenerated).
- [ ] Paused-at-final_review send-back behavior unchanged (regression).
- [ ] Rule-/behavior tests prove the broken cases FAIL pre-fix and PASS post-fix.
- [ ] `bash scripts/ci/gates.sh backend` green + `/qa-agent` PASS.

## Gherkin Scenarios

See `backend/tests/features/carousel_pipeline_consolidation.feature`
(`@cp-final-review` additions for approved/END send-back + feedback keying).

## Affected Areas

- Backend: editorial workflow resume/feedback + engine re-entry.
- Tests: unit (persist keying, engine re-entry) + integration (routing + feedback)
  + `.feature` scenarios.
- Frontend: none | API: none (same endpoint) | Deployment: none beyond redeploy.

## Dependencies

- Related: AE-0285 (GLM provider — repetitive GLM content is what surfaced this),
  AE-0286 (copy trim).

## Implementation Plan

1. Write RED tests: persist keying under target; engine re-entry from END.
2. Fix #1 (feedback keying) + Fix #2 (engine goto from END).
3. Add `.feature` scenarios; extend integration send-back test to assert routing +
   feedback keying + image preservation.
4. `gates.sh backend` + `/qa-agent`; then re-drive prod carousel a2991a39.

## Progress Log

### 2026-06-30

Ticket created from live prod diagnosis (carousel a2991a39). Root cause traced to
feedback keying + approved/END re-entry. Images confirmed decoupled/reusable.

## Files Touched

- `agents/carousel_workflow_graph.py` (approved_hold node + route_after_hold)
- `agents/carousel_workflow_nodes.py` (approved_hold_phase; send-back drops
  publish approval; clear send_back_target on re-approval)
- `agents/carousel_workflow_engine.py` (get_state masks the hold)
- `domain/constants/carousel_workflow.py` (PHASE_APPROVED_HOLD)
- `application/services/carousel/editorial_workflow_{feedback,types,service,
  service_helpers}.py` (target-phase feedback keying + synchronous publish-lock)
- tests: `test_carousel_workflow.py`, `test_carousel_workflow_phases.py`,
  `test_editorial_workflow_support.py`, `test_editorial_workflow_service.py`,
  `test_workflow_validation.py`, `carousel_pipeline_consolidation.feature`

## Test Evidence

`gate-capture.sh backend` → 15 PASS / 0 FAIL / 4 SKIP (Postgres-only; CI-run).
Full suite locally: 2455 passed, 4 skipped. mutation ≥75% PASS; integrity PASS.
Probe-verified: reach hold (publishable) → send-back → content regenerates once
→ workflow_status=draft → re-approve → back to hold (send_back_target cleared) →
revise-without-target → finalize safely (no stale-publish). See
`.agent/reports/AE-0288.qa.md`.

## QA Report

PASS (external, opencode-go/glm-5.2, 3 rounds FAIL→WARN→PASS). See
`.agent/reports/AE-0288.qa.md`.

## Decision Log

- **2026-06-30 — abandoned engine `goto` re-entry of ended graphs.** External QA
  (opencode-go/glm-5.2) flagged the `Command(goto=target,resume=...)` branch. A
  realistic-runner probe proved it makes the graph run straight through every gate
  back to END and re-approve (regenerating with no human review + re-locking
  publish) — and prod confirmed it (the first send-back this session re-approved
  without regenerating). Tested 10 mechanisms (goto±resume, two-step reopen,
  `aupdate_state(as_node)+ainvoke(None)`, sentinel-reopen, checkpoint-fork rewind);
  all unreliable. Reverted.
- **Chose the final-review HOLD instead.** Validated by probe: reach hold; send-back
  → content with exactly one regeneration; re-approve → back to hold (no stale-
  target loop, guarded by the `quality_passed`/`approved` precedence); finalize →
  END. Then verified on the real engine: `get_state` reports
  `final_review`/`approved`/`approved_for_publish` while held.

## Blockers

None.

## Final Summary

Approved carousels now park at an internal `approved_hold` interrupt instead of
terminating, so a final-review send-back reliably re-enters the targeted phase
and regenerates (images reused per-slide by prompt hash). `get_state` masks the
hold (reports final_review/approved), so the carousel stays publishable; any
send-back drops the publish approval in graph state for the whole revision
window. Validated by 10+ probes, full suite (2455), green gates, and 3 external
QA rounds (FAIL→WARN→PASS). Limitation: does not retro-fix already-terminated
carousels (e.g. prod a2991a39 — needs a one-off).
