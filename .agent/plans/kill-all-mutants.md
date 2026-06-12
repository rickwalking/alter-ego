# Plan to Kill All Survived Mutants — AE-0028 Epic

**Date:** 2026-06-10
**Current Score:** 1197/1999 killed (60%)
**Target Score:** 1800+/1999 killed (90%+)
**Survived Mutants:** 795

---

## Priority 1: EditorialWorkflowService (234 mutants)

### 1.1 `resume_workflow` — 86 survived
**Root Cause:** Complex method with many branches (validation, revision cap, persona score, presentation validation, event publishing, orchestrator delegation). Current tests only cover 3 rejection paths and 1 success path.
**Plan:**
- Add test for revision cap not exceeded (survives `revision_count < cap` mutants)
- Add test for persona score >= threshold (survives `score < threshold` → `score <= threshold`)
- Add test for presentation validation non-blocking (survives `blocking` check mutants)
- Add test for event publishing with valid resume (survives `emit_review_event` call mutants)
- Add test for `resume_workflow` with `db` parameter (survives `db is None` mutants)
- Add test for `resume_workflow` with `workflow_input` parameter (survives `workflow_input` mutants)
- Add test for `resume_workflow` returning updated state (survives state update mutants)

### 1.2 `start_workflow` — 60 survived
**Root Cause:** Method has multiple branches for new vs existing workflows, research synthesis, and state initialization. Only tested for existing state.
**Plan:**
- Add test for starting new workflow (survives `get_state` is None branch)
- Add test for starting workflow with `research_findings` (survives `synthesize_research` call)
- Add test for starting workflow with `workflow_input` (survives `workflow_input` mutants)
- Add test for starting workflow with `db` (survives `db` parameter mutants)
- Add test for start workflow with `brief` parameter (survives `brief` mutants)

### 1.3 `_sync_project_phase` — 46 survived
**Root Cause:** Not directly tested in any unit test. Called by `mark_resume_in_progress` but mocked out.
**Plan:**
- Add direct test for `_sync_project_phase` with `db` parameter
- Add test for `_sync_project_phase` with `project` parameter
- Add test for `_sync_project_phase` with `project_id` parameter
- Add test for `_sync_project_phase` when `phase_status` is updated
- Add test for `_sync_project_phase` when `current_phase` is updated
- Add test for `_sync_project_phase` error handling

### 1.4 `mark_resume_in_progress` — 16 survived
**Root Cause:** Partially tested, but some branches are mocked.
**Plan:**
- Add test for `mark_resume_in_progress` with `db` parameter
- Add test for `mark_resume_in_progress` when `get_state` returns None
- Add test for `mark_resume_in_progress` when `_sync_project_phase` is called
- Add test for `mark_resume_in_progress` when phase is not awaiting_human
- Add test for `mark_resume_in_progress` when `publish_workflow_phase_change` is called

### 1.5 `publish_resume_error_event` — 13 survived
**Root Cause:** Not directly tested.
**Plan:**
- Add test for `publish_resume_error_event` with different error types
- Add test for `publish_resume_error_event` when `events` is None
- Add test for `publish_resume_error_event` with `project_id` and `error` parameters

### 1.6 `get_workflow_state` — 7 survived
**Root Cause:** Already tested but some branches not covered.
**Plan:**
- Add test for `get_workflow_state` when `get_state` returns None
- Add test for `get_workflow_state` when `phase` is empty string
- Add test for `get_workflow_state` when DB merge is skipped
- Add test for `get_workflow_state` with `project` parameter

### 1.7 `__init__` — 5 survived
**Root Cause:** Constructor not tested with different parameters.
**Plan:**
- Add test for `__init__` with `llm` parameter
- Add test for `__init__` with `checkpointer` parameter
- Add test for `__init__` with `events` parameter
- Add test for `__init__` with `notifications` parameter
- Add test for `__init__` with `image_registry` parameter

### 1.8 `stream_phase_updates` — 1 survived
**Root Cause:** SSE streaming method not tested.
**Plan:**
- Add test for `stream_phase_updates` returning async generator
- Add test for `stream_phase_updates` with `project_id` parameter

---

## Priority 2: Module-Level Functions (176 mutants)

### 2.1 `editorial_workflow_service.py` — Module-level functions
**Root Cause:** Helper functions like `emit_review_event`, `create_workflow_trace`, `publish_workflow_phase_change` are not directly tested.
**Plan:**
- Add test for `emit_review_event` with different parameters
- Add test for `emit_review_event` when `events` is None
- Add test for `create_workflow_trace` with `project_id` and `reviewer_id`
- Add test for `publish_workflow_phase_change` with `project_id`, `phase`, `status`
- Add test for `publish_workflow_phase_change` when `publish` is None

### 2.2 `editorial_workflow_support.py` — Module-level functions
**Root Cause:** Re-export hub with many module-level functions.
**Plan:**
- Add tests for SSE builder functions
- Add tests for SSE publish functions
- Add tests for SSE format functions

### 2.3 `editorial_workflow_routes_support.py` — Module-level functions
**Root Cause:** Re-export hub with many module-level functions.
**Plan:**
- Add tests for sanitize functions
- Add tests for response builder functions
- Add tests for validation functions

### 2.4 `editorial_distribution_pack.py` — Module-level functions
**Root Cause:** Distribution functions not directly tested.
**Plan:**
- Add tests for `slide_data_from_draft` with different inputs
- Add tests for `blog_data_from_draft` with different inputs
- Add tests for generation functions
- Add tests for persist functions

---

## Priority 3: QualityAgent (96 mutants)

### 3.1 `evaluate` / `evaluate_eeat` — 40+ survived
**Root Cause:** Complex evaluation methods with many branches.
**Plan:**
- Add test for `evaluate` with different criteria
- Add test for `evaluate_eeat` with different scores
- Add test for `evaluate_eeat` when `calculate_originality` returns different values
- Add test for `evaluate_eeat` when `_ai_evaluate` returns different responses

### 3.2 `_parse_evaluation_response` — 20+ survived
**Root Cause:** JSON parsing with fallback logic.
**Plan:**
- Add test for `_parse_evaluation_response` with invalid JSON
- Add test for `_parse_evaluation_response` with missing fields
- Add test for `_parse_evaluation_response` with extra fields

### 3.3 `_cosine_similarity` — 15 survived
**Root Cause:** Math function not fully tested.
**Plan:**
- Add test for `_cosine_similarity` with orthogonal vectors
- Add test for `_cosine_similarity` with negative values
- Add test for `_cosine_similarity` with zero vectors
- Add test for `_cosine_similarity` with identical vectors

### 3.4 `generate_improvement_suggestions` — 10 survived
**Root Cause:** Not directly tested.
**Plan:**
- Add test for `generate_improvement_suggestions` with different scores
- Add test for `generate_improvement_suggestions` when score is None

### 3.5 `calculate_originality` — 10 survived
**Root Cause:** Not directly tested.
**Plan:**
- Add test for `calculate_originality` with different embeddings
- Add test for `calculate_originality` with zero vectors

---

## Priority 4: FeedbackLearningLoop (94 mutants)

### 4.1 `record_correction` — 25 survived
**Root Cause:** Complex method with input sanitization and repository calls.
**Plan:**
- Add test for `record_correction` with `correction_type` parameter
- Add test for `record_correction` when `correction_type` is None
- Add test for `record_correction` with `project_id` parameter
- Add test for `record_correction` when `sanitize_llm_input` modifies text
- Add test for `record_correction` with non-string `_persona_id`

### 4.2 `suggest_improvements` — 25 survived
**Root Cause:** Not directly tested.
**Plan:**
- Add test for `suggest_improvements` with empty entries
- Add test for `suggest_improvements` with entries but no embeddings
- Add test for `suggest_improvements` with similar entries

### 4.3 `classify_correction` — 15 survived
**Root Cause:** Not fully tested with all branches.
**Plan:**
- Add test for `classify_correction` with `conciseness` case (already covered)
- Add test for `classify_correction` with `tone` case (already covered)
- Add test for `classify_correction` with `content` case (already covered)
- Add test for `classify_correction` with `minor_edit` case (not covered)
- Add test for `classify_correction` when corrected text is same length

### 4.4 `_load_entries` — 5 survived
**Root Cause:** Not directly tested.
**Plan:**
- Add test for `_load_entries` with empty rows
- Add test for `_load_entries` with multiple rows

### 4.5 `_to_stored` — 5 survived
**Root Cause:** Static method not directly tested.
**Plan:**
- Add test for `_to_stored` with different row types

### 4.6 `__init__` — 5 survived
**Root Cause:** Not tested.
**Plan:**
- Add test for `__init__` with different parameters

### 4.7 `get_relevant_examples` — 5 survived
**Root Cause:** Already tested but not fully.
**Plan:**
- Add test for `get_relevant_examples` with `_k` parameter
- Add test for `get_relevant_examples` with non-string `_persona_id`

### 4.8 `_cosine_similarity` — 5 survived
**Root Cause:** Already tested but not fully.
**Plan:**
- Add test for `_cosine_similarity` with zero vectors
- Add test for `_cosine_similarity` with negative vectors

### 4.9 `analyze_voice_drift` — 10 survived
**Root Cause:** Already tested with 8 new tests but some mutants still survive.
**Plan:**
- Add test for `analyze_voice_drift` with threshold boundary (drift_score = 0.2)
- Add test for `analyze_voice_drift` with multiple samples where one pair is identical

---

## Priority 5: BlogPostAIService (77 mutants)

### 5.1 `suggest` — 30 survived
**Root Cause:** Complex method with JSON parsing and prompt building.
**Plan:**
- Add test for `suggest` with invalid JSON response
- Add test for `suggest` with `trace` parameter
- Add test for `suggest` with `context` parameter
- Add test for `suggest` with different actions

### 5.2 `improve` — 25 survived
**Root Cause:** Complex method with persona loading.
**Plan:**
- Add test for `improve` with persona loading
- Add test for `improve` with invalid action
- Add test for `improve` with `trace` parameter

### 5.3 `generate_image` — 20 survived
**Root Cause:** Already tested but some branches not covered.
**Plan:**
- Add test for `generate_image` with `user_id` parameter
- Add test for `generate_image` when image generation fails

### 5.4 `_load_persona` — 2 survived
**Root Cause:** Already tested but some branches not covered.
**Plan:**
- Add test for `_load_persona` with `persona_id` parameter

---

## Priority 6: PersonaAgent (58 mutants)

### 6.1 `evaluate_match` — 20 survived
**Root Cause:** Not directly tested.
**Plan:**
- Add test for `evaluate_match` with different scores
- Add test for `evaluate_match` when score is below threshold

### 6.2 `_build_style_guide` — 20 survived
**Root Cause:** Not directly tested.
**Plan:**
- Add test for `_build_style_guide` with different persona profiles
- Add test for `_build_style_guide` with empty profile

### 6.3 `enforce` — 15 survived
**Root Cause:** Already tested but not fully.
**Plan:**
- Add test for `enforce` with different content types
- Add test for `enforce` when `evaluate_match` returns low score

### 6.4 `_parse_evaluation_response` — 3 survived
**Root Cause:** Already tested but not fully.
**Plan:**
- Add test for `_parse_evaluation_response` with invalid JSON

---

## Priority 7: CarouselRefinementMixin (45 mutants)

### 7.1 `refine_carousel_copy` — 20 survived
**Root Cause:** Not directly tested.
**Plan:**
- Add test for `refine_carousel_copy` with different slide indices
- Add test for `refine_carousel_copy` with invalid slide index

### 7.2 `refine_carousel_design` — 15 survived
**Root Cause:** Not directly tested.
**Plan:**
- Add test for `refine_carousel_design` with different design tokens
- Add test for `refine_carousel_design` with invalid tokens

### 7.3 `regenerate_slide_image` — 10 survived
**Root Cause:** Not directly tested.
**Plan:**
- Add test for `regenerate_slide_image` with different slide indices
- Add test for `regenerate_slide_image` when image generation fails

---

## Priority 8: CarouselEditorialOrchestrator (15 mutants)

### 8.1 `start` — 8 survived
**Root Cause:** Not directly tested.
**Plan:**
- Add test for `start` with `db` parameter
- Add test for `start` with `workflow_input` parameter
- Add test for `start` with `brief` parameter

### 8.2 `resume` — 1 survived
**Root Cause:** Not directly tested.
**Plan:**
- Add test for `resume` with `db` parameter

### 8.3 `get_state` — 1 survived
**Root Cause:** Already tested but not fully.
**Plan:**
- Add test for `get_state` when `get_state` returns None

### 8.4 `_bind_resume_context` — 6 survived
**Root Cause:** Not directly tested.
**Plan:**
- Add test for `_bind_resume_context` with `db` parameter
- Add test for `_bind_resume_context` with `workflow_input` parameter

---

## Implementation Order

1. **Phase 1 (Week 1):** EditorialWorkflowService (234 mutants)
   - Start with `_sync_project_phase` (46) — easiest to kill
   - Then `mark_resume_in_progress` (16) and `publish_resume_error_event` (13)
   - Then `resume_workflow` (86) and `start_workflow` (60)

2. **Phase 2 (Week 2):** Module-Level Functions (176 mutants)
   - Start with `editorial_workflow_service.py` helpers
   - Then `editorial_workflow_support.py` and `editorial_workflow_routes_support.py`
   - Then `editorial_distribution_pack.py`

3. **Phase 3 (Week 3):** QualityAgent (96 mutants) + FeedbackLearningLoop (94 mutants)
   - Start with `FeedbackLearningLoop.classify_correction` (15) and `_cosine_similarity` (5)
   - Then `QualityAgent._cosine_similarity` (15) and `_parse_evaluation_response` (20)
   - Then `FeedbackLearningLoop.record_correction` (25) and `suggest_improvements` (25)

4. **Phase 4 (Week 4):** BlogPostAIService (77) + PersonaAgent (58) + CarouselRefinementMixin (45) + CarouselEditorialOrchestrator (15)
   - Start with `BlogPostAIService.suggest` (30) and `improve` (25)
   - Then `PersonaAgent.evaluate_match` (20) and `_build_style_guide` (20)
   - Then `CarouselRefinementMixin` methods (45)
   - Finally `CarouselEditorialOrchestrator` (15)

---

## Expected Results

| Phase | Mutants | Expected Killed | Cumulative Score |
|-------|---------|----------------|-------------------|
| Current | 795 | 0 | 60% |
| Phase 1 | 234 | 180 (77%) | 1377/1999 = 69% |
| Phase 2 | 176 | 120 (68%) | 1497/1999 = 75% |
| Phase 3 | 190 | 140 (74%) | 1637/1999 = 82% |
| Phase 4 | 195 | 150 (77%) | 1787/1999 = 89% |

**Target:** 89% mutation score after 4 phases.

---

## Risk Mitigation

1. **Orchestration Layer:** EditorialWorkflowService methods have complex state machines. Tests may need to mock the orchestrator more carefully.
2. **Async Methods:** `mark_resume_in_progress`, `stream_phase_updates` are async. Tests need `pytest.mark.asyncio`.
3. **External Dependencies:** Some methods depend on LangGraph, Langfuse, or OpenAI. Use `unittest.mock` for these.
4. **File Size:** New tests should be in separate test files, not exceeding 400 lines.

---

## Tracking

- **Phase 1:** Start 2026-06-10, End 2026-06-17
- **Phase 2:** Start 2026-06-17, End 2026-06-24
- **Phase 3:** Start 2026-06-24, End 2026-07-01
- **Phase 4:** Start 2026-07-01, End 2026-07-08

---

**Author:** QA Agent
**Status:** Draft — Awaiting approval
