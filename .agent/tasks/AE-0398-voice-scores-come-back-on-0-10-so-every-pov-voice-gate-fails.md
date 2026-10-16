# AE-0398 — Voice scores come back on 0-10 so every POV voice gate fails

Status: In Development
Tier: T1
Priority: P0
Type: Bug
Area: backend
Owner: Claude (owner-requested hotfix)
Agent Lane: developer → qa → release
Branch: fix/ae-0398-voice-score-scale
Kanban Card: TBD
Created: 2026-10-16
Updated: 2026-10-16

## Goal

On-voice content passes the voice gate (floor 70 on 0-100).

## Problem

Prod 2026-10-16 (run b241ded5, project 98a2e2f0): once AE-0397 let the content phase score the voice, the scores came back as overall 8.2-8.9 per slide. The scoring prompt does not name the scale, so the model answered on 0-10. Every check compares against `VOICE_MATCH_MIN_SCORE = 70.0`: the autopilot gate (`policy`) and the engine's content approval. The autopilot therefore sent on-voice copy back for a rewrite, and a manual approval would have been refused too.

## Scope

- `PersonaAgent._parse_evaluation_response`: when all five scores are at most 10, the answer is read as 0-10 and every score is multiplied by 10. All-zero and unreadable answers stay 0 (the gate still fails closed). The prompt is not changed (prompt files are versioned).

## Non-Goals

- Changing the threshold or the scoring prompt.

## Acceptance Criteria

- [x] AC1: A 0-10 answer is scaled to 0-100.
- [x] AC2: A 0-100 answer is unchanged.
- [x] AC3: An all-zero or unreadable answer stays 0.
- [x] AC4: On-voice copy scored 8.2 on 0-10 passes the floor of 70.

## Gherkin Scenarios

`backend/tests/features/persona_score_scale_ae0398.feature` (4 scenarios).

## Delta

### ADDED

- `backend/tests/unit/agents/test_persona_score_scale_ae0398.py`, the feature file

### MODIFIED

- `backend/src/rag_backend/agents/persona_agent.py`

### REMOVED

- None.

## Affected Areas

- Backend: persona scoring
- Frontend: none
- Database: none
- API: none
- Tests: unit + feature
- Docs: this ticket
- Prompts/LLM: none (parsing only)
- Observability: none
- Deployment: none

## Dependencies

- Blocks: POV autopilot runs passing the content gate
- Blocked by: none
- Related: AE-0397, AE-0371

## Implementation Plan

1. Normalize the parsed scores to 0-100.
2. Unit tests and a feature file.

## QA Checklist

- [x] Security reviewed (parsing only)
- [x] Code quality reviewed
- [x] Acceptance criteria validated
- [x] Edge cases tested (0-100 kept, zero, unreadable)
- [x] Orphan/unfinished code checked

## Progress Log

### 2026-10-16 10:30

Found from the prod run's persona_scores; fixed and tested.

## Files Touched

See Delta.

## Test Evidence

- `test_persona_score_scale_ae0398.py` + `test_persona_agent.py`: 54 passed.
- Unit suite: 3977 passed, 0 failed.

## QA Report

Pending (hotfix fast path: CI Test & Coverage decides).

## Decision Log

- 2026-10-16: Normalize in the parser instead of editing the prompt, because prompt files are versioned and this fix is deterministic.

## Blockers

None.

## Final Summary

Pending.
