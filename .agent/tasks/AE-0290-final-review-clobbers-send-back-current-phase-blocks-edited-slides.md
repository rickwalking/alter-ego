# AE-0290 — final_review clobbers send-back current_phase, blocking edited slides

Status: Dev Complete
Tier: T1
Priority: P1
Type: Bugfix
Area: backend
Owner: Unassigned
Agent Lane: architect → developer → qa → release
Branch: fix/ae-0290-final-review-preserve-send-back-phase
Created: 2026-07-01
Updated: 2026-07-01

## Goal

Make a final-review send-back to the content phase correctly record
`current_phase=content` in the checkpoint so `edited_localized_slides` are accepted
(no spurious 422), without disturbing the approval / approved-hold behavior.

## Scope

- `agents/carousel_workflow_nodes.py` → `final_review_phase` only.
- Backend unit/`.feature` tests for the send-back / approval phase transitions.

## Non-Goals

- No change to `read_checkpoint_phase` / `get_state` pending-next semantics.
- No change to the content/images/other phase nodes or graph routing.
- No change to the edited-slides gate itself (`ensure_structured_feedback_allowed`).
- No frontend changes.

## Problem

On a final-review send-back to the content phase, `edited_localized_slides` are
rejected with 422 `edited_localized_slides_content_phase_only` even though the
reviewer explicitly routed back to `content`.

Root cause — `final_review_phase` **hardcodes** `current_phase = final_review`,
clobbering the send-back's `current_phase = content`:

`agents/carousel_workflow_nodes.py:354-357`
```python
result: dict[str, object] = {
    **review_update,                 # already carries current_phase="content" on send-back
    "quality_passed": approved,
    "current_phase": PHASE_FINAL_REVIEW,   # <-- BUG: overwrites the send-back target
    ...
```

Mechanics of the failure:
1. `review_updates_from_response` (`carousel_workflow_nodes.py:122-127`) sets
   `current_phase = content` from `structured_feedback.target_phase`.
2. `final_review_phase` commits `current_phase = final_review` (line 357),
   overwriting it in the checkpoint `values`.
3. Graph routes final_review → content; `content_phase` hits `interrupt()` and
   **suspends before committing** its own `current_phase = content`.
4. Last committed checkpoint value is therefore `final_review`.
5. `read_checkpoint_phase` (`application/services/carousel/editorial_workflow_feedback.py:28-37`)
   reads the raw value (deliberately ignoring the pending-next override) → returns
   `final_review`.
6. Gate `ensure_structured_feedback_allowed`
   (`api/routes/carousels/editorial_workflow_routes_validate.py:250-254`) sees
   `checkpoint_phase != PHASE_CONTENT` and raises 422
   `ERR_EDITED_SLIDES_CONTENT_ONLY`
   (`domain/constants/carousel_workflow.py:67`).

Discovered while fixing prod carousel `a2991a39` (AE-0288/AE-0289 follow-up).
Note: `approved_hold_phase` (`carousel_workflow_nodes.py:372-391`) does NOT have
this clobber, so the bug only fires on a send-back taken at the *first*
final_review interrupt (before the approved-hold park).

## Fix (proposed)

Preserve the send-back target in `final_review_phase`: only set
`current_phase = PHASE_FINAL_REVIEW` when there is **no** send-back target;
otherwise honor `review_update`'s `current_phase`.

```python
send_back_target = review_update.get(SEND_BACK_TARGET_PHASE_KEY)
result: dict[str, object] = {
    **review_update,
    "quality_passed": approved,
    "workflow_status": (...),
    "status": "draft",
}
if not send_back_target:
    result["current_phase"] = PHASE_FINAL_REVIEW
```

This keeps `current_phase = final_review` on approval/plain resume (approval path
also still clears `SEND_BACK_TARGET_PHASE_KEY`, line 368) and lets the checkpoint
correctly read `content` after a send-back so the edited-slides gate passes. The
fix does NOT clear `send_back_target_phase` on a content send-back — routing
(`route_after_final_review`, `carousel_workflow_graph.py:73-85`) still needs it.

**Guard (external QA):** validate the preserved `send_back_target` is a member of
`CAROUSEL_WORKFLOW_PHASES` before honoring it, so a stale/corrupted-but-truthy
target can't set `current_phase` to a bogus value.

Rejected alternative: teaching `read_checkpoint_phase` to honor pending-next like
`CarouselWorkflowEngine.get_state` (engine.py:196-197). More surface area, and it
would make the raw checkpoint value and the gate disagree on the *persisted*
truth; fixing the write site is cleaner.

**Combined payload semantic (external QA — document, don't change):** if a reviewer
sends `target_phase=content` AND `edited_localized_slides` in the *same*
final-review send-back, line 250 still fires (checkpoint is `final_review` at that
instant) → 422. Intended flow is two-step: send back to content first, then submit
edited slides once parked at content. Called out so it isn't mistaken for a bug.

## Acceptance Criteria

- [x] After a final-review send-back with `target_phase = content`, the checkpoint
      `current_phase` reads `content` and `edited_localized_slides` are accepted
      (no 422 `edited_localized_slides_content_phase_only`).
- [x] `send_back_target_phase` is still **set** (not cleared) on a content
      send-back, so `route_after_final_review` routes correctly.
- [x] Positive regression: the `has_final_review_fields` send-back gate
      (`editorial_workflow_routes_validate.py:245`) still **accepts** a
      `target_phase` send-back submitted at the `final_review` checkpoint.
- [x] Approval / plain resume still records `current_phase = final_review` and
      clears `send_back_target_phase` (AE-0288 behavior intact).
- [x] Send-back to non-content phases (images) routes correctly and still does
      **not** accept `edited_localized_slides` (gate still fires for them).
- [x] Preserved `send_back_target` outside `CAROUSEL_WORKFLOW_PHASES` is rejected
      (membership guard), not written to `current_phase`.
- [x] `gates.sh backend` green + external QA.

## Test Evidence

`gate-capture.sh backend` → 15 PASS / 0 FAIL / 4 SKIP (test/diff-cover/migrations/
schema-drift SKIP locally — need Postgres; CI runs them). Integrity: 0 net-new
blockers.

`GATES_JSON: {"pass":15,"fail":0,"skip":4,"results":[{"gate":"backend:format","status":"PASS"},{"gate":"backend:lint","status":"PASS"},{"gate":"backend:lint-diff","status":"PASS"},{"gate":"backend:blanket-ignore","status":"PASS"},{"gate":"backend:strict-diff","status":"PASS"},{"gate":"backend:type","status":"PASS"},{"gate":"backend:imports","status":"PASS"},{"gate":"backend:arch-ratchet","status":"PASS"},{"gate":"backend:docstrings","status":"PASS"},{"gate":"backend:dead-code","status":"PASS"},{"gate":"backend:inline-prompts","status":"PASS"},{"gate":"backend:bandit","status":"PASS"},{"gate":"backend:pip-audit","status":"PASS"},{"gate":"backend:integrity","status":"PASS"},{"gate":"backend:test","status":"SKIP"},{"gate":"backend:diff-cover","status":"SKIP"},{"gate":"backend:migrations","status":"SKIP"},{"gate":"backend:schema-drift","status":"SKIP"},{"gate":"backend:mutation","status":"PASS"}]}`

Targeted: `test_carousel_workflow_phases.py` (3 new AE-0290 cases: content send-back
preserves `content`; images send-back preserves `images`; bogus target falls back
to `final_review`) + `test_editorial_workflow_structured_feedback_gate.py` (3 new:
target_phase accepted at final_review; edited slides accepted at content; edited
slides rejected at final_review). Full unit suite: 2100 passed, 1 skipped.

## Gherkin / Tests

Behavior-changing bugfix → `.feature` required. Cover:
- send-back to content → gate allows edited slides (happy path)
- approval → current_phase=final_review, send_back target cleared (regression)
- send-back to images → edited slides still rejected (edge)

Extend `tests/unit/agents/test_carousel_workflow_phases.py` and
`tests/unit/application/test_editorial_workflow_support.py`.

## Files Touched (expected)

- `agents/carousel_workflow_nodes.py` (`final_review_phase`)
- `tests/features/*.feature` + the two unit test modules above.

## Related

AE-0288 (send-back content regen), AE-0289 (edited-slides sanitizer).
Memory: [[carousel-send-back-feedback-keying-bug]].
