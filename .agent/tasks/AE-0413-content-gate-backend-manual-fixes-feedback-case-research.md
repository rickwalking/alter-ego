# AE-0413 — Content gate backend: manual fixes on the first gate, edits that stick, content-note history, case-preserving LLM inputs, PT/EN research

Status: In Development
Tier: T1
Priority: P0
Type: Bug
Area: backend
Owner: Claude (fix agent, QA 2026-10-16)
Agent Lane: developer → qa → release
Branch: fix/ae-0413-content-gate-backend
Kanban Card: TBD
Created: 2026-10-17
Updated: 2026-10-17

## Goal

The content gate does what the UI promises: manual fixes are accepted on the first content
gate, applied as-is and re-validated without any regeneration or translation. Content notes
reach the model and stay visible after use. Generated copy is not lowercase because of our
own inputs. Research only keeps Portuguese/English, on-topic web sources.

## Problem

QA run 2026-10-16 (`~/alter-ego-qa/2026-10-16-ui/REPORT.md`):

- **B02 (blocker)**: "Enviar correções manuais" on the FIRST content gate → 422
  `edited_localized_slides_phase_not_allowed`, while `state.current_phase == "content"`.
- **B03 (major)**: manual fixes re-ran content generation/localization: EN copy became
  Portuguese, `summary_points` dropped, `slide_parse_failed` appeared. After a content revision
  the EN copy was Portuguese on all slides without a `wrong_language` violation.
- **B16 (major)**: `phase_feedback.content` stayed `[]` after content revisions with feedback.
- **B12 (major)**: copy systematically lowercase (≈30 sentence-case blockers per run); the
  violation message claimed the text "was auto-capitalized" while it was not.
- **B14 (major)**: research accepted Russian, off-topic sources (the search keyed on the
  "[QA 2026-10-16]" prefix) and they reached the outline and the blog markdown.

## Root causes (verified on main 6e7c144)

- **B02**: LangGraph never commits an interrupted node's return value. On the first content
  gate the checkpoint's stored `current_phase` was still `outline` (set by the outline node).
  `get_state` overrides it with the pending node (`content`), but `read_checkpoint_phase`
  ("ignores pending_next override") returned the raw `outline`, so the guard 422'd. After one
  revision the content node had completed once, so the stored value became `content` (202).
- **B03**: after the review update applied the edits, the revise re-entered the content node
  and its ensure ran: with no new notes it did not regenerate, but it rebuilt `localized_slides`
  from the PT drafts with `translations_en=None` (only fresh translations were passed), so the
  builder's EN payload fell back to the PT draft; it ran the fail-closed LLM re-draft on every
  blocking slide (Slide 2 replaced → `slide_parse_failed`, items lost). Validator: the
  `wrong_language` rule needed 4+ words and 2+ PT stopwords, so short Portuguese EN headings
  passed, while the autofix (`looks_portuguese`) already treated 1 stopword + accent as PT.
- **B16**: by design since AE-0405, `phase_feedback[phase]` holds only ACTIVE notes; a note the
  regeneration used moves to `phase_feedback_history` (status `applied`). The note does reach
  the drafting prompt (`revision_notes` → instruction "revision" block), but the history was
  not exposed on the API, and the fail-closed single-slide re-draft did not receive the notes.
- **B12**: `sanitize_llm_input` lowercased everything (it matched injection phrases on a
  lowercased copy). Topic, audience, brief (route + outline agent), sources and reviewer
  feedback reached the prompts lowercase; the model mirrored it. The casing-marker message
  claimed an auto-capitalization the reviewer could not see.
- **B14**: `_search_topic_sources` searched the raw topic and kept the top 3 hits with no
  language or relevance check.

## Scope

1. `read_checkpoint_phase` reads the phase of the gate the graph is parked at
   (`checkpoint_gate_phase`); the parked content checkpoint stores `current_phase=content`.
2. A manual-fixes revise (edits only, no new content note, no send-back) parks the edited,
   re-validated artifacts, so the content re-entry reuses them (no ensure, no LLM call).
3. A content ensure that does not regenerate keeps the stored `translations_en`; the
   fail-closed re-draft gets the active notes.
4. EN copy that `looks_portuguese` is reported (`wrong_language`, or `translation_not_english`
   on contracts without `wrong_language`).
5. `phase_feedback_history` is served on the workflow state response (additive).
6. `sanitize_llm_input` preserves case; injection phrases still removed (case-insensitive,
   repeated until stable), `< > ( )` stripped, length capped. Casing message rewritten.
7. Web-search query drops bracketed tags and emoji; hits must be PT/EN (Latin-script ratio +
   stopwords) and share a keyword stem with the query. Owner sources are never filtered.

## Non-Goals

- Frontend (AE-0414 owns the content review UI, B04 truncation, i18n of error codes).
- B01 persona score scales (AE-0411+ / other ticket).

## Acceptance Criteria

- [x] AC1: research → outline → content → manual edit on the FIRST content gate is accepted
  (`read_checkpoint_phase == "content"`), regression test on the real engine.
- [x] AC2: a manual fix keeps the edited PT/EN copy byte-for-byte, leaves other slides
  unchanged, re-validates, and calls neither the content ensure nor the drafting model.
- [x] AC3: approval after a manual fix commits the edited copy; a revise with a note still
  regenerates with that note.
- [x] AC4: a non-regenerating content ensure uses the stored EN translations, never the PT draft.
- [x] AC5: Portuguese EN headings are reported by the validator on every content result.
- [x] AC6: consumed content notes are served as `phase_feedback_history`; the re-draft gets notes.
- [x] AC7: LLM inputs keep case; injection phrases are removed case-insensitively.
- [x] AC8: the casing message no longer claims an auto-capitalization.
- [x] AC9: bracketed tags are not searched; foreign-language and off-topic hits are discarded
  without consuming the 3-hit cap; owner sources are kept.

## Gherkin Scenarios

`backend/tests/features/content_gate_backend_ae0413.feature`

## Delta

### ADDED

- `agents/research_relevance.py`, `api/routes/carousels/editorial_workflow_routes_feedback.py`,
  `domain/carousel_gate_phase.py` (`checkpoint_gate_phase`, shared by engine-side and guard-side code
  without a cross-layer import)
- `PhaseFeedbackHistoryEntryResponse` + `EditorialWorkflowStateResponse.phase_feedback_history`
- Feature file and tests (`test_content_gate_manual_fixes_ae0413.py`,
  `test_content_gate_backend_ae0413.py`, research relevance tests)

### MODIFIED

- `agents/carousel_content_park.py` (pins content phase; `manual_fixes_park_updates`)
- `agents/carousel_workflow_nodes.py`, `agents/research_enrichment.py`, `agents/input_sanitizer.py`
- `application/services/carousel/editorial_workflow_feedback.py`, `phase_artifact_runner.py`,
  `copy_hygiene_text.py`, `presentation_content_rules.py`, `presentation_casing_markers.py`
- `api/routes/carousels/editorial_workflow_routes_sanitize.py`, `editorial_workflow_routes_response.py`
- `domain/constants/content_feedback.py`, `domain/constants/research_enrichment.py`
- Tests whose expectations encoded the lowercasing (blog AI service, generate_carousel tool,
  input sanitizer) and the parked-update shape.
- Docs: `docs/backend/content-feedback-lifecycle.md`, `docs/backend/slide-copy-validators.md`,
  `docs/architecture/openapi.json` (regenerated).

### REMOVED

- None.

## Affected Areas

- Backend: editorial workflow content gate, research enrichment, sanitizer
- Frontend: none in this PR; AE-0414 can read `phase_feedback_history`
- Database: none (checkpoint state only)
- API: additive `phase_feedback_history` on the workflow state response; resume contract unchanged
- Tests: unit + feature
- Docs: lifecycle + validators + openapi
- Prompts/LLM: inputs keep case; fewer LLM calls on manual fixes
- Observability: `content_manual_fixes_kept`, `research_hit_filtered`
- Deployment: none

## Dependencies

- Blocks: AE-0414 (content review UI) relies on the 202 on the first content gate
- Blocked by: none
- Related: AE-0289, AE-0290, AE-0310, AE-0366, AE-0403, AE-0405

## Implementation Plan

1. Feature file. 2. Regression tests on the real engine. 3. Checkpoint gate phase.
4. Manual-fixes park. 5. Translations + re-draft notes. 6. Language check.
7. History field. 8. Sanitizer + message. 9. Research filter. 10. Gates.

## QA Checklist

- [ ] Security reviewed (sanitizer keeps the anti-injection intent)
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-10-17

Ticket created from the QA report; root causes verified on main; fix implemented
(hotfix fast path, see Test Evidence).

## Files Touched

See Delta.

## Test Evidence

See the dev summary in the PR description (gate run).

## QA Report

Pending.

## Decision Log

- **Guard reads the pending gate, not the raw stored phase.** It is the phase the API shows
  and the one the reviewer acts on; the approved hold keeps `final_review` (AE-0288).
- **Manual fixes reuse the parked marker** instead of a new state flag: the marker already
  means "the next content entry reuses these artifacts" (AE-0405).
- **Edit payloads still replace a locale payload** (no key overlay): the completed-project
  edit endpoint (AE-0314) relies on replace semantics to drop items, and the content review UI
  sends whole payloads. The dropped items came from the ensure rebuild, which no longer runs.
- **`phase_feedback` keeps its AE-0405 meaning (active notes)**; the history is exposed
  instead of re-filling the active list (which would re-feed the next regeneration).
- **Research filter is heuristic and conservative**: Latin-script ratio ≥ 0.8, a PT/EN stopword
  when the hit has 8+ words, and one shared 5-letter keyword stem with the query.

## Blockers

None.

## Final Summary

Pending.
