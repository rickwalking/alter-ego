# AE-0588 — Generated slide copy fits the slide length budgets

Status: Dev Complete
Tier: T2
Priority: High
Type: Feature
Area: Backend
Owner: Pedro Marins
Agent Lane: developer → qa → release
Branch: feat/ae-0588-copy-fits-slide-budgets
Kanban Card: TBD
Created: 2026-11-01
Updated: 2026-11-01

## Goal

A freshly generated carousel reaches the content gate with copy that already
fits the slide length budgets of its presentation contract, in PT and EN,
without loosening any validator, threshold, severity, contract or gate.

## Problem

Prod QA run of 2026-11-01 (see AE-0499, "Related evidence": run 2 was blocked
by the presentation validation): a fresh POV carousel stopped at the content
gate with blocking presentation violations because the generated copy was
25-40% over the budgets on several slides at once:

- slide 1 PT body 237 chars vs a budget of about 180; EN body 245 vs about 180;
- headings 77 / 87 chars over a 60-72 budget;
- slide 2 `summary_points[i].body` 99-123 chars vs 76-90;
- plus `copy_truncated` and `emphasis_unbalanced` left by the mechanical trims.

Root causes found in the code:

1. The drafting prompts list the contract budgets only as one global block
   (`render_presentation_policy_context`), never "this slide's fields and their
   limits"; the POV content prompts (`carousel_pov/v1`, `carousel_pov_news/v1`)
   also hardcode their own numbers, one of which contradicts the contract
   (sub-hook "até 80 caracteres" vs `intro_subtitle` 40 in `pov_hook_v1`).
2. The translation prompt (`carousel/v9/slide_translations.yaml`) only says
   "keep each text about as long as its Portuguese source"; it gets no limit.
3. Nothing rewrites an over-budget field before validation: the bounded
   deterministic repair trims by cutting (ellipsis, which `copy_truncated`
   blocks, so the trim is discarded), and the targeted field repair runs only
   after the gate has already blocked, sharing its rounds with every other
   blocker.

## Pedro's decision (2026-11-01)

Fix the root cause: content generation must fit the slide length budgets by
itself. (a) The drafting and translation prompts state each field's budget
per slide type, taken from the same contract values the validator uses. (b)
An automatic shorten step runs before the presentation validation: every
over-budget field is rewritten by the fast model within its budget, re-checked,
at most 2 attempts, and whatever remains goes to the normal validation.
Validators and thresholds stay exactly as they are; mechanical truncation is
not the fix.

## Design

**Single source of the numbers.** A new pure module
`copy_budget_limits.py` resolves a field's limit with the validator's own
resolvers (`heading_budget_for_slide_type`, `body_budget_for_slide_type`, the
item budget keys via `field_budget`) plus the word rules the validator applies
(`HOOK_MAX_WORDS` on the PT heading of the slide whose contract role is
`hook`, as `presentation_deck_rules.py` checks it, when `hook_word_limit` is active,
`MIN_CONTENT_BODY_WORDS` on a content body when `body_too_short` is active).
No number is written anywhere else.

**(a) Prompt budgets.**

- Drafting: the instruction context's per-slide block (`_slide_block`, already
  sized to the deck) appends "Copy limits of this slide", rendered by the new
  versioned template `carousel_copy_budget/v1/slide_limits.yaml` from
  `slide_field_limits(slide_type, policy)`. Every content prompt family (v6
  fixed contracts, v7 Radar IA, POV, POV news) gets it through the instruction.
- POV content prompts: new `carousel_pov/v3/content.yaml` and
  `carousel_pov_news/v3/content.yaml` drop the hardcoded per-role numbers
  (one contradicted the contract) and point at the limits block; v1 stays for
  rollback. New constant `POV_PROMPT_CONTENT_VERSION = "v3"`; outline and
  caption keep `POV_PROMPT_VERSION`.
- Translation: each slide sent to the translator carries `limits` (field ->
  max characters / lines, from the same resolver for the slide's type and
  the drafts' policy version); new `carousel/v10/slide_translations.yaml`
  tells the model every English field must fit its limit (shorter sentence,
  same meaning, never cut). `CAROUSEL_TRANSLATION_PROMPT_VERSION` -> v10.

**(b) Shorten step before the presentation validation.** In
`PhaseArtifactRunner._ensure_content_artifacts`, after the drafts, EN
translations and state sanitize, and right before
`_build_presentation_review_updates` (the fail-closed validate -> repair ->
retry chain):

1. Build the localized slides from the drafts + translations exactly as the
   review build does (`build_localized_slides_with_failures` +
   `recover_parse_failures`); slides with an unrecovered parse failure are
   left to the existing chain.
2. Validate with the real validator; targets are the fields with
   `heading_too_long`, `body_too_long` or `copy_too_many_lines` (heading, body,
   `features|summary_points|actions[i].title|body`, PT and EN), via
   `plan_targets` (same field paths and limits as the gate repair). On a
   scoped revision only the scoped slides are touched.
3. One fast-model call per attempt carries all remaining targets (prompt
   `carousel_copy_budget/v1/fit_fields.yaml`: limit, current text, problems,
   slide heading, PT source for EN, the author's style guide with forbidden
   phrases). Answer format `{"fixes": [{"id", "text"}]}` (gate repair parser).
4. Acceptance per field, checked by code: non-empty and different; an EN
   answer that reads Portuguese is dropped; strictly shorter (or fewer lines)
   than the current text; adds no persona forbidden phrase; and re-validating
   the patched slide adds no new violation `(locale, field, code)` anywhere on
   the slide (so a broken `**`, a missing final punctuation, a body under the
   minimum words, a hook over 10 words, a repeated heading are all rejected).
   **Best effort** = the shortest accepted rewrite; a rejected answer leaves
   the field as it was. Never a mechanical cut.
5. Re-check, at most `COPY_BUDGET_FIT_MAX_ATTEMPTS = 2` attempts, stop early
   when nothing is over budget; a model error or timeout keeps the copy.
6. Changed slides are written back to the drafts and EN translations through
   `apply_localized_slide_edits` (the owner-edit path), so drafts, translations
   and the review build stay in step; the normal chain then validates them.
7. Persona: the shortened copy is not passed through `PersonaAgent.enforce()`
   (a free rewrite would undo the budgets). Instead the prompt carries the
   style guide, forbidden phrases are rejected deterministically, and the
   persona voice scores are recomputed after the step for the slides whose
   copy changed (unchanged slides keep their score by fingerprint). A slide
   whose new score is under `VOICE_MATCH_MIN_SCORE` (70) while its old score
   met it goes back to its old draft, translation and score (no model call).
   The exemption is recorded in ADR-0030 (proposed, amends ADR-003).
8. Owner hook: the PT heading of the hook slide is never a target when the
   content mode has a chosen `hook_text`, or when it equals the approved
   outline's slide-1 title; an over-budget one blocks. EN may be shortened.
9. A PT answer that reads as English is rejected, like an EN answer that
   reads as Portuguese; a timeout keeps the copy.

Model: fast role (`roles.fast`, same as the gate repair); `temperature` and
`max_tokens` are bound from `fit_fields.yaml`; the call is traced with
`get_langfuse_runnable_config("copy budget fit")` (inside the phase trace that
carries `project_id`, `phase`, `agent_name`, `user_id`, `content_type`).
Enabled when the orchestrator passes `budget_fit_tracing`, injectable in tests.
Logs: `copy_budget_fit_attempt` (fields asked) and `copy_budget_fit_done`
(attempts, asked, accepted, rejected, still over budget, changed slides).

LangGraph: the step is pure computation plus one model call inside the
content ensure, before the interrupt; it has no external side effect, and the
parked-review replay reuses the stored artifacts (no re-run). No `interrupt()`
is wrapped.

## Scope

- `copy_budget_limits.py`, `copy_budget_fit.py`, `copy_budget_fit_llm.py`,
  `copy_budget_fit_drafts.py` (new, application layer) and constants.
- Prompts: `carousel_copy_budget/v1/{slide_limits,fit_fields}.yaml` + README,
  `carousel/v10/slide_translations.yaml` + README,
  `carousel_pov/v3/content.yaml` + README, `carousel_pov_news/v3/content.yaml` + README.
- Wiring: instruction loader slide block, translation payload, POV content
  version, phase artifact runner.

## Non-Goals

- Changing any validator, threshold, severity, contract, rule or gate.
- Changing the deterministic bounded repair, the gate field repair, owner
  autofix or the refinement / autofix re-translate paths.
- Editing an existing prompt version file.

## Acceptance Criteria

- [x] AC1 Drafting prompts state this slide's field limits (chars, lines,
  words) rendered from the contract through the validator's resolvers; a
  changed contract value changes the prompt.
- [x] AC2 The translation request carries each slide's field limits and the
  v10 prompt requires English to fit them.
- [x] AC3 POV content v3 prompts carry no hardcoded character numbers; v1 kept.
- [x] AC4 Before the presentation validation, every over-budget field (PT and
  EN, heading, body and nested items) is rewritten by the fast model; fields
  within budget are never sent.
- [x] AC5 At most 2 attempts; a still-too-long rewrite is kept only if it is
  shorter and adds no violation (best effort); a rewrite that breaks emphasis,
  punctuation or any other rule is rejected; a model failure keeps the copy.
- [x] AC6 Changed slides are written back to drafts and EN translations; the
  persona voice score is recomputed for changed slides and a slide that drops
  under 70 from at least 70 is reverted; forbidden phrases are rejected.
- [x] AC9 The owner's PT hook heading (picked hook or approved outline title)
  is never rewritten; EN may be.
- [x] AC7 Validators, thresholds, severities and contracts unchanged.
- [x] AC8 Regression test with the QA evidence shapes ends with no length
  violation.

## Gherkin Scenarios

See `backend/tests/features/copy_fits_slide_budgets_ae0588.feature`.

## Delta

### ADDED

- `backend/src/rag_backend/application/services/carousel/copy_budget_limits.py`
- `backend/src/rag_backend/application/services/carousel/copy_budget_fit.py`
- `backend/src/rag_backend/application/services/carousel/copy_budget_fit_llm.py`
- `backend/src/rag_backend/application/services/carousel/copy_budget_fit_drafts.py`
- `backend/src/rag_backend/domain/constants/copy_budget_fit.py`
- `backend/src/rag_backend/agents/prompts/carousel_copy_budget/` (README, v1)
- `backend/src/rag_backend/agents/prompts/carousel/v10/` (README, slide_translations)
- `backend/src/rag_backend/agents/prompts/carousel_pov/v3/`, `carousel_pov_news/v3/` (README, content)
- `backend/src/rag_backend/application/services/carousel/content_budget_step.py`
- `docs/decisions/0030-persona-check-for-budget-field-rewrites.md` (proposed, amends ADR-003)
- Feature file and unit tests.

### MODIFIED

- `instruction_context_loader.py` (slide limits in the slide block),
  `editorial_distribution_generation.py` (limits in the translation payload),
  `carousel_template/prompts.py` (two prompt builders),
  `content_draft_agent.py` (POV content version), `phase_artifact_runner.py`
  (fit step + persona rescore), `domain/constants/carousel.py`,
  `domain/constants/pov_prompts.py`.

### REMOVED

- None.

## Affected Areas

- Backend: carousel content phase.
- Frontend: none.
- Database: none.
- API: none.
- Tests: new unit + integration-style tests.
- Docs: prompt READMEs.
- Prompts/LLM: new prompt versions; one extra fast-model call per attempt.
- Observability: Langfuse-traced call, two structlog events.
- Deployment: none.

## Dependencies

- Blocks: none.
- Blocked by: none.
- Related: AE-0499 (QA evidence), AE-0430 (gate field repair), AE-0401 (copy rules), ADR-0030 (proposed).

## Implementation Plan

1. Feature file.
2. Limits resolver + prompt blocks (drafting, translation, POV v3).
3. Fit loop + LLM adapter + draft adapter.
4. Wire into the content ensure; persona rescore.
5. Tests, gates, dev summary.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-11-01

Ticket created with the design (Pedro's decision, 2026-11-01). Implemented
(98efa2325), integrity fix for 3 `type: ignore` in the new tests (ed2ee3c58).
Full `gate-capture.sh backend` at ed2ee3c58: 26 pass, 0 fail, 1 skip (mutation,
CI only). Moved to Dev Complete.

## Files Touched

See Delta.

## Test Evidence

48 new unit tests (fake models only) in
`backend/tests/unit/application/test_{copy_budget_fit,copy_budget_prompts,copy_budget_fit_drafts,content_budget_step}_ae0588.py`;
`tests/unit/application` + `tests/unit/agents`: 3242 passed. See
`.agent/reports/AE-0588.dev-summary.md`.

GATES_JSON: {"pass":26,"fail":0,"skip":1,"results":[{"gate":"backend:format","status":"PASS"},{"gate":"backend:lint","status":"PASS"},{"gate":"backend:lint-diff","status":"PASS"},{"gate":"backend:blanket-ignore","status":"PASS"},{"gate":"backend:strict-diff","status":"PASS"},{"gate":"backend:type","status":"PASS"},{"gate":"backend:imports","status":"PASS"},{"gate":"backend:arch-ratchet","status":"PASS"},{"gate":"backend:docstrings","status":"PASS"},{"gate":"backend:dead-code","status":"PASS"},{"gate":"backend:inline-prompts","status":"PASS"},{"gate":"backend:gherkin-refs","status":"PASS"},{"gate":"backend:comments","status":"PASS"},{"gate":"backend:blog-v1-dead-code","status":"PASS"},{"gate":"backend:redis-factory","status":"PASS"},{"gate":"backend:autopilot-env","status":"PASS"},{"gate":"backend:healthcheck-loopback","status":"PASS"},{"gate":"backend:openapi-fresh","status":"PASS"},{"gate":"backend:bandit","status":"PASS"},{"gate":"backend:pip-audit","status":"PASS"},{"gate":"backend:integrity","status":"PASS"},{"gate":"backend:duplication","status":"PASS"},{"gate":"backend:test","status":"PASS"},{"gate":"backend:diff-cover","status":"PASS"},{"gate":"backend:migrations","status":"PASS"},{"gate":"backend:schema-drift","status":"PASS"},{"gate":"backend:mutation","status":"SKIP"}]}

## QA Report

Pending.

## Decision Log

- Role-level numbers in the POV v1 prompts (rehook 90, point/twist 160) are
  not contract values; v3 replaces them with qualitative guidance so the only
  numbers the model sees are the contract's.
- The shorten step reuses the gate repair's target planner and answer parser
  but has its own prompt and acceptance rules (length-only, per-field
  re-validation, shorter-only, forbidden phrases).

## Blockers

None.

## Final Summary

Pending.
