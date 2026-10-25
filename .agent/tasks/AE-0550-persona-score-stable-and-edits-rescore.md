# AE-0550 — The persona voice gate is stable, and a hand edit can clear it

Status: In Development
Tier: T1
Priority: High
Type: Bug
Area: Backend
Owner: QB
Branch: fix/ae-0550-rescore-edited-slides
Created: 2026-10-25
Updated: 2026-10-25

## Goal

The content approve gate (voice score ≥ 70 per slide) reflects the slide copy the owner sees: the same copy gets
the same score, and a hand edit that improves the voice clears the gate without an LLM revision.

## Problem

Carousel `2fe43d2c` (2026-10-25): slide 9 scored 62, so approve was disabled (frontend `persona-score.ts` →
`create-workflow-panel-state.ts`; backend `validate_content_approve_persona_score`). Two separate causes:

1. **Hand edits never re-score.** "Submit manual fixes" re-enters the content node with the parked marker, and the
   replay reuses the reviewed artifacts by design (`carousel_content_park.py`, `_content_ensure_or_reuse`): no
   regeneration and no scoring, so the pre-edit score stays and the gate can only be cleared by paying for a revise.
2. **The scorer is noisy and reads the wrong text.** After one revise that targeted slide 9 only, unchanged slides
   moved: 1: 90 → 38, 4: 86 → 50, 5: 73 → 45, and slide 8 (copy unchanged) scored 15. Investigation:
   - **Which text:** `_score_slides` judged `draft_text` only: the PT body, with no heading and no checklist items
     (a hand edit mirrors only the edited PT body into it). A checklist slide was judged on a near-empty line.
   - **Determinism:** the judge ran at the chat models' default temperature 0.7 (`chat_model_factory._TEMPERATURE`).
   - **Re-scoring unchanged slides:** every content entry re-judged every slide, even when a revise was scoped to one.
   - **The prompt** (inline in `PersonaAgent.evaluate_match`) never named the scale (the parser already had to guess
     0-10 vs 0-100) and did not say what to judge, so length and formatting pulled short slides down.

Pedro had to approve past the gate because of this.

## Scope

- `persona_slide_scoring.py`: the judged text is the slide's visible PT copy (heading, body, every checklist item;
  falls back to title + `draft_text`); each stored entry carries the fingerprint of the text it judged; a slide whose
  copy matches its last entry keeps that entry and is not judged again (an entry without a fingerprint, unscored, or
  marked `rescore_pending` by the autopilot is judged again).
- `PhaseArtifactRunner._score_slides` delegates there (reuse on every content entry) and
  `rescore_edited_content(state)` re-scores on the parked replay: only the edited slides change text, so only they
  are judged.
- The edits-only revise re-scores in the content node's own return, after the edits apply
  (`_rescore_after_manual_fixes` in `content_phase_async`), so the new scores reach the checkpoint. The parked replay
  never scores (a replay's interrupt payload is not persisted, and it re-paid the judge on every replay).
- A judge that gives no score keeps the slide's previous entry marked `rescore_pending` (still gating on its last score;
  a timeout never opens the gate). A failed render of the judge prompt is logged before the inline fallback.
- The judged copy is PT only and includes the TL;DR strip; stats and insight quotes are left out on purpose. Temperature
  0 may be ignored by reasoning models; the fingerprint reuse is the stabiliser.
- The judge runs at temperature 0 (`PERSONA_JUDGE_TEMPERATURE`) with a new prompt `persona/v1/evaluate.yaml` that
  names the 0-100 scale with anchors and asks for the voice only.

## Non-Goals

- Changing the 70 threshold or the gate UI.
- The autopilot's own slide-fix re-score path (it keeps its `rescore_pending` markers).

## Acceptance Criteria

- [x] AC1 Same copy, same score: unchanged slides keep their entries and the judge is not called
  (`test_unchanged_slides_keep_their_scores_without_a_judge_call`, `test_only_the_changed_slide_is_judged`).
- [x] AC2 An edit that improves the voice clears the gate: only the edited slide is judged, the others keep their
  scores, and `validate_content_approve_persona_score` stops refusing (`test_an_edit_that_improves_the_voice_clears_the_gate`);
  the parked replay re-scores instead of regenerating (`test_the_parked_replay_rescores_instead_of_regenerating`).
- [x] AC3 The judge reads heading, body and items (`test_the_judge_reads_the_visible_copy`).
- [x] AC4 Stale, unscored or pending entries are judged again (`test_a_stale_or_unscored_entry_is_judged_again`).
- [x] AC5 The judge call runs at temperature 0 with the 0-100 prompt (`test_evaluate_match_prompt_exact_format`).
- [x] AC6 Engine level: submit manual fixes → `get_state()["persona_scores"]` holds the new score of the edited slide,
  the others are unchanged, the judge ran once, and approve is no longer refused
  (`test_submit_manual_fixes_persists_the_new_score_and_clears_the_gate`; seeded: fails at the previous head with 62).
- [x] AC7 A judge timeout keeps the last score as `rescore_pending` and approval is still refused
  (`test_a_failed_rejudge_keeps_the_last_score_pending`).

## Repro Steps

1. Content gate with a slide under 70; hand-edit that slide and submit the edits only.
2. Before: the score is unchanged and approve stays disabled. After: only that slide is re-judged.

## Affected Areas

- [x] Backend
- [ ] Frontend
- [x] Tests

## Dependencies

None.

## Progress Log

### 2026-10-25 01:30

Ticket created from Pedro's two reports; fix and tests written.

## Files Touched

- `backend/src/rag_backend/application/services/carousel/persona_slide_scoring.py` (new)
- `backend/src/rag_backend/application/services/carousel/phase_artifact_runner.py`
- `backend/src/rag_backend/agents/carousel_workflow_nodes.py`
- `backend/src/rag_backend/agents/persona_agent.py`, `backend/src/rag_backend/agents/prompts/persona/v1/evaluate.yaml` (new)
- `backend/src/rag_backend/domain/constants/persona.py`
- tests: `test_persona_score_stability_ae0550.py`, `test_persona_rescore_engine_ae0550.py` (new) + feature, `test_persona_agent.py`,
  `test_content_scoring_ae0439.py`, `test_persona_judge_ae0407.py`, `test_autopilot_unscored_judge_flow_ae0433.py`,
  `test_carousel_slide_fix_ae0401.py`, `test_carousel_workflow.py`

## Test Evidence

See `.agent/reports/AE-0550.dev-summary.md`.

## QA Report

Pending.

## Blockers

None.
