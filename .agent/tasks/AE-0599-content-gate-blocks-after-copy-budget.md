# AE-0599 — Content gate blocks after the copy budget step

Status: Dev Complete
Tier: T2
Priority: High
Type: Bug
Area: Backend
Owner: Pedro Marins
Agent Lane: developer → qa → release
Branch: fix/ae-0599-content-gate-after-budget
Kanban Card: TBD
Created: 2026-11-02
Updated: 2026-11-02

## Goal

A freshly generated carousel reaches the content gate with copy that fits its
slide budgets and with each locale's emphasis in its own convention, so the gate
passes honestly. The gate, its limits, the voice threshold of 70, the forbidden
phrases and the ADR-0030 checks stay exactly as they are.

## Problem

After the AE-0588 deploy (2026-11-02 13:31Z, PR #334) every autopilot carousel
was blocked at the content gate; the 12 gates before it had 0 violations.
Read-only triage of the prod checkpoints (counts, codes and 8-char ids only):

| Carousel | Mode | First gate | Codes |
|---|---|---|---|
| `6f36130e` | pov | 31 | body_too_long 9 PT + 9 EN, heading_too_long 2 + 2, emphasis_markup_locale_mismatch 9 EN |
| `d8da820a` | pov | 39 | body_too_long 13 + 13, emphasis_markup_locale_mismatch 12 EN, heading_too_long 1 EN |
| `41c4f437` | pov_news | 1 | translation_shape_mismatch (slide 4) |

(`d8da820a` went 39 → 8 → 6 through the later gate repairs and was published;
`41c4f437` passed after an owner revision; `6f36130e` escalated.)

### Root cause

1. **The drafting model returned bilingual blobs, now on most slides.** A draft
   whose `draft_text` is a JSON object with PT and EN payloads is turned into
   `presentation_pt` + `presentation_en` by the malformed-draft normalizer, and
   `_resolve_en_source` then prefers that model-written EN over the EN
   translation. Before AE-0588: 8 of 108 slides (12 runs) were blobs, all of
   them body-only. After: 12 of 18 POV slides (`6f36130e` slides 3, 4, 5, 7, 8;
   `d8da820a` slides 1, 2, 4, 5, 6, 8, 9), with feature lists on "point" slides
   and long headings. **Every one of the 70 first-gate violations of
   `6f36130e` and `d8da820a` sits on a blob slide.** The AE-0588 slide limits
   block lists `features[].title` / `features[].body` on every content slide and
   says the limits "apply to the Portuguese and to the English copy"; the POV
   v3 prompt dropped the role-level targets v1 had and only points at that
   block in the instruction. The blob copy came back 1.5 to 2.7 times over the
   budgets (bodies 287 to 540 characters against 200, summary point bodies 149
   to 322 against 90, headings 71 to 78 against 64).
2. **The blob EN uses the PT emphasis markers, and nothing converts them while a
   length blocker remains.** The translation path converts PT `**` to EN
   `<strong>`; the blob EN skips the translation. The bounded review repair does
   convert, but all-or-nothing per payload: on a payload that still has a length
   blocker the whole repair, conversion included, is discarded, so every
   emphasized EN field stays an `emphasis_markup_locale_mismatch`. `<strong>` is
   13 characters longer than `**`, and the shorten step measured EN with the
   `**` it had: on `d8da820a` slide 5 even a perfect shorten leaves the EN item
   titles over 32 characters once converted, so the conversion is discarded
   again (reproduced: 4 mismatches left with a cooperative fit model).
3. **The shorten step landed no rewrite on any blob slide in prod.** Rebuilding
   the stored drafts and running the real step with a fit model that changes
   nothing reproduces both prod first gates field for field (31 and 39); with a
   cooperative fit model the same drafts end at 0 (`6f36130e`) and 4 (`d8da820a`,
   the cause 2 mismatches). Why the prod rewrites did not land (timeout, parse
   failure, code rejection or a voice revert) is not recoverable: the step logs
   went with the container restart before the triage and the Langfuse traces
   are outside the read-only grant. The step now logs every rejection by reason
   and every voice revert.

Why the earlier gates had 0 violations: blob slides were rare and carried only a
heading and a body, so the bounded repair could trim the body at a sentence
boundary and convert the EN emphasis in the same pass (for example a 499
character blob body validated at 182). The new blobs carry item lists and long
headings, which the deterministic repair cannot shorten, so it discards the
whole payload repair.

`41c4f437` is a separate defect: slide 4's EN translation kept a quote card
(`insight`) that its PT draft no longer had (PT recovered from a scaffold as an
empty feature list). No length or markup code is involved and the copy budget
step does not touch the structure; it is reported, not fixed, here.

## Pedro's decision (2026-11-02)

Fix only the generation side: prompt and budget alignment, the shorten step and
emphasis markup kept in step across locales. Do not relax the content gate, its
validators, limits or thresholds, nor the ADR-0030 checks. If a limit had to
change, stop and report.

## Design

- **Emphasis in each locale's convention before measuring**
  (`copy_budget_emphasis.py`, used by `fit_slides_to_budgets`): every balanced
  pair is converted with `normalize_emphasis` (the conversion the review repair
  applies) on the allowed slides before the targets are planned, so EN is
  measured with the `<strong>` it renders with; a field the tags push over its
  budget becomes a shorten target. Every fit answer gets the same conversion
  before it is checked. Excluded addresses (the owner's PT hook heading) are
  never touched. Slides changed by the conversion are written back like
  shortened ones (drafts + EN translations, persona rescore, voice guard).
- **Diagnostics:** the done log carries `rejected_reasons` (`unchanged`,
  `wrong_language`, `not_shorter`, `forbidden_phrase`, `new_violation`); a voice
  revert logs `copy_budget_fit_voice_reverted` with its slides.
- **Prompts (new versions, defaults switched):**
  `carousel_copy_budget/v2/slide_limits.yaml` (item limits are not a request to
  add items; emphasis markup cost per locale) and `carousel_pov/v4`,
  `carousel_pov_news/v4` `content.yaml` (this slide's contract limits rendered
  inline before the answer format through the `slide_limits` variable, count
  the characters, items only when the role asks). v1 and v3 are kept.
- Unchanged: validators, limits, severities, contracts, `VOICE_MATCH_MIN_SCORE`,
  the forbidden-phrase and voice checks, `fit_fields.yaml` (v1), the gate
  repair, the bounded repair.

## Scope

- `copy_budget_emphasis.py` (new), `copy_budget_fit.py`, `content_budget_step.py`,
  `instruction_context_loader.py` (`slide_limits_text`), `content_draft_agent.py`
  (`slide_limits` variable), `carousel_template/prompts.py` (limits version),
  constants (`copy_budget_fit.py`, `pov_prompts.py`).
- Prompts: `carousel_copy_budget/v2/`, `carousel_pov/v4/`, `carousel_pov_news/v4/`.

## Non-Goals

- Any change to the content gate, a validator, a limit, a severity, a contract,
  the voice threshold, the forbidden phrases or the ADR-0030 checks.
- The `41c4f437` quote-card shape mismatch (separate follow-up).
- The EN heading casing check reading `<strong>` as a lowercase start (a gate
  rule; reported for an owner decision, not changed).
- Editing an existing prompt version file.

## Acceptance Criteria

- [x] AC1 Before measuring, the shorten step puts every balanced emphasis pair
  in its locale's convention; EN fields reach the fit model in `<strong>` and a
  field the tags push over budget is a target.
- [x] AC2 Every fit answer is converted to its locale's convention before it is
  checked; the owner's PT hook heading is never touched.
- [x] AC3 Rebuilt from the recorded prod shapes, `6f36130e` and `d8da820a`
  pass the content gate after the step with a cooperative fit model; with the
  fit model down they block on length only, never on emphasis.
- [x] AC4 `41c4f437`: the quote card stays in both locales through the step and
  the gate reports only its separate slide 4 shape mismatch.
- [x] AC5 The POV content prompts (v4) carry this slide's contract limits inline
  before the answer format; the v2 limits block states that item limits are not
  a request to add items and the markup cost per locale; defaults switched,
  v1/v3 kept.
- [x] AC6 Rejections are logged by reason and voice reverts with their slides.
- [x] AC7 Gate, validators, limits, voice threshold, forbidden phrases and
  ADR-0030 checks unchanged.

## Gherkin Scenarios

See `backend/tests/features/content_gate_after_copy_budget_ae0599.feature`.

## Delta

### ADDED

- `backend/src/rag_backend/application/services/carousel/copy_budget_emphasis.py`
- `backend/src/rag_backend/agents/prompts/carousel_copy_budget/v2/` (slide_limits, README)
- `backend/src/rag_backend/agents/prompts/carousel_pov/v4/`, `carousel_pov_news/v4/` (content, README)
- `backend/tests/features/content_gate_after_copy_budget_ae0599.feature`
- `backend/tests/unit/application/gate_shape_specs_ae0599.py`, `gate_shape_builder_ae0599.py`
- `backend/tests/unit/application/test_content_gate_after_budget_ae0599.py`, `test_copy_budget_emphasis_ae0599.py`

### MODIFIED

- `copy_budget_fit.py`, `content_budget_step.py`, `instruction_context_loader.py`,
  `content_draft_agent.py`, `carousel_template/prompts.py`,
  `domain/constants/copy_budget_fit.py`, `domain/constants/pov_prompts.py`,
  `agents/prompts/carousel_copy_budget/README.md`,
  `tests/unit/application/test_copy_budget_prompts_ae0588.py` (POV default pin v3 → v4).

### REMOVED

- None.

## Affected Areas

- Backend: carousel content phase (shorten step, drafting prompt variables).
- Frontend: none.
- Database: none.
- API: none.
- Tests: new feature, fixtures and unit tests.
- Docs: prompt READMEs.
- Prompts/LLM: new prompt versions; no new LLM call (the fit call keeps its
  `copy budget fit` Langfuse trace).
- Observability: `rejected_reasons` in `copy_budget_fit_done`, new
  `copy_budget_fit_voice_reverted`.
- Deployment: none.

## Dependencies

- Blocks: none.
- Blocked by: none.
- Related: AE-0588 (copy budgets), ADR-0030, AE-0430 (gate repair).

## Implementation Plan

1. Feature file, fixtures from the recorded shapes, failing tests.
2. Emphasis conversion in the shorten step, answer conversion, diagnostics.
3. New prompt versions, defaults switched.
4. Gates, dev summary.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-11-02

Read-only triage of the three blocked carousels, root cause above. Feature,
fixtures rebuilt from the recorded shapes and failing tests (4 failing on the
pre-fix code), then the fix (1ac1cab82, 19de7a7b2). Full
`gate-capture.sh backend` at 19de7a7b2: 26 pass, 0 fail, 1 skip (mutation, CI
only).

## Files Touched

See Delta.

## Test Evidence

See `.agent/reports/AE-0599.dev-summary.md`.

GATES_JSON: {"pass":26,"fail":0,"skip":1,"results":[{"gate":"backend:format","status":"PASS"},{"gate":"backend:lint","status":"PASS"},{"gate":"backend:lint-diff","status":"PASS"},{"gate":"backend:blanket-ignore","status":"PASS"},{"gate":"backend:strict-diff","status":"PASS"},{"gate":"backend:type","status":"PASS"},{"gate":"backend:imports","status":"PASS"},{"gate":"backend:arch-ratchet","status":"PASS"},{"gate":"backend:docstrings","status":"PASS"},{"gate":"backend:dead-code","status":"PASS"},{"gate":"backend:inline-prompts","status":"PASS"},{"gate":"backend:gherkin-refs","status":"PASS"},{"gate":"backend:comments","status":"PASS"},{"gate":"backend:blog-v1-dead-code","status":"PASS"},{"gate":"backend:redis-factory","status":"PASS"},{"gate":"backend:autopilot-env","status":"PASS"},{"gate":"backend:healthcheck-loopback","status":"PASS"},{"gate":"backend:openapi-fresh","status":"PASS"},{"gate":"backend:bandit","status":"PASS"},{"gate":"backend:pip-audit","status":"PASS"},{"gate":"backend:integrity","status":"PASS"},{"gate":"backend:duplication","status":"PASS"},{"gate":"backend:test","status":"PASS"},{"gate":"backend:diff-cover","status":"PASS"},{"gate":"backend:migrations","status":"PASS"},{"gate":"backend:schema-drift","status":"PASS"},{"gate":"backend:mutation","status":"SKIP"}]}

## QA Report

Pending.

## Decision Log

- The emphasis conversion is the deterministic one the review repair already
  applies; doing it before measuring is a generation-side change, the gate
  still checks the result.
- Not PT-only drafting: the drafting parser keeps only `draft_text`, so item
  lists can only arrive inside a JSON draft; a PT-only flat blob would copy PT
  into EN. The prompts instead discourage unrequested items and state the EN
  markup cost.

## Blockers

None.

## Final Summary

Pending.
