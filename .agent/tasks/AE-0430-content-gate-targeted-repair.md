# AE-0430 — Content gate violations survive generation and revision; no targeted repair

Status: Done
Tier: T1
Priority: P1
Type: Bug
Area: Backend
Owner: Claude (owner-reported prod hotfix, 2026-10-19)
Agent Lane: developer → qa → release
Branch: feat/ae-0430-content-gate-targeted-repair
Kanban Card: TBD
Created: 2026-10-19
Updated: 2026-10-19

## Goal

When the carousel content gate blocks, the failing fields (and only those) are repaired by
the model within their exact limits, a "Feedback para revisão" run actually uses the
violations, EN keeps the PT structured shape, no label scaffolding reaches visible copy, and
anything still blocking is fixable by hand in the editor.

## Problem

Owner report (prod, 2026-10-19), carousel `5344b6c6-1d66-4b0e-9989-93f1316f8829`
(`news_analysis`, `hero_lower_third_v4`, phase `content`, `awaiting_human`). Read-only export:
`/home/pmarins/alter-ego-qa/2026-10-19-carousel-5344/state.json`.

- Two human notes ("Revise os textos com erros de validação e corrija todos", "Fix them:
  Slides para corrigir: Slide 1, 2, 6") are `applied`, `revision_count.content = 2`, yet
  `content_gate_validation` still holds 12 blockers.
- Slide 1: `translation_shape_mismatch` (PT `intro:tldr`, EN `intro:plain`); the EN column of
  the manual editor has no TL;DR field, so the owner cannot fix it.
- `slide_drafts[0].draft_text` starts with `**PT**\n\n**heading:** …`; `**PT**` ends up in the
  visible PT body.
- Over-length fields: EN heading 83/72, EN body 258/180 (slide 1), `features[*].body`
  105-121/100 (slide 3), `actions[*].body` 106-145/90 (slide 6), PT and EN.

### Root causes (file:line on `origin/main`, d1bf11c91)

1. **No targeted repair (A).** The content ensure's only model step on a blocked gate is
   the fail-closed chain's one whole-slide re-draft
   (`application/services/carousel/content_fail_closed.py:158`, `:176`). It is not given the
   violations or the limits, and nothing re-validates and repairs per field afterwards.
2. **Revision ignores the violations (B).** `PhaseArtifactRunner._regen_inputs`
   (`phase_artifact_runner.py:227`) passes only the owner's note text to the drafting
   model, never the concrete violations or limits. The note is then marked `applied`
   unconditionally (`phase_artifact_runner.py:344`), even when the copy did not improve.
3. **EN loses structured fields (C).** The translation payload sends only heading/body/notes
   (`editorial_distribution_generation.py:104`) and the parser keeps only heading/body
   (`:131`). The localized builder copies the draft's top-level `tldr_strip` into PT
   (`localized_slide_builder.py:160`) but builds EN from that translation
   (`:241`), so a TL;DR intro always comes back `intro:plain` in EN.
4. **Editor cannot fix it (D).** The editable EN column renders only the extras the EN
   payload already has (`content-phase-locale-fields.tsx:91`), so a missing EN TL;DR has no
   input.
5. **Label leak (E).** Scaffold recovery recognises locale sections only as `## PT`
   (`slide_scaffold_recovery.py:54`). With `**PT**` headers the section split fails, the
   label stripper (`:109`) keeps the `**PT**` line, and the deterministic trim then cuts
   the body ("**PT**\nTodo mundo viu …").
6. **Over-length (item 4 of the brief).** The v6 translation prompt has no length guidance
   (`carousel/v6/slide_translations.yaml:12`). Neither the drafter nor the translator is
   ever told which field broke which budget after validation (root cause 1). The
   validator and its limits are correct and stay unchanged.

## Scope

- A. `content_gate_repair.py` / `content_gate_repair_targets.py` /
  `content_gate_repair_flow.py`: a targeted field repair loop. It runs whenever the
  content ensure ends blocked (first drafting, translation, revision). It sends only the
  failing fields, each with path, current text, exact limit, problems, slide heading and
  PT source. It patches by path, re-validates, runs at most 2 rounds and ≤40 fields per
  round, never truncates and never raises. It writes back like owner edits. The prompt
  lives in the registry (`carousel_gate_repair/v1/field_repair.yaml`). Tracing goes
  through the orchestrator-injected Langfuse runnable config (`get_langfuse_runnable_config`).
- B. The revision request carries the blocking violations, one line each
  (`gate_violation_note`). The repair loop runs after the regeneration. The note is
  `applied` only when the visible copy changed; otherwise `unchanged` (new history status).
- C. The translator sends and returns `tldr_strip` and item texts (new prompt
  `carousel/v8/slide_translations.yaml`; v6 kept). Every EN translation gets the PT draft's
  structured extras (translated if the answer has the same shape, PT otherwise). A residual
  mismatch is filled from PT inside the repair loop and translated.
- D. The editable EN (and PT) column mirrors every structured field the other locale has
  (empty texts, PT icons); an edit materialises it (`mirrorLocaleStructure`).
- E. `**PT**` / `**EN**` bold-only lines are locale section headers; an EN payload built
  from the draft takes the EN section heading instead of the PT title.

## Non-Goals

- Loosening any validator rule or budget; truncating copy.
- Touching prod data, re-running the owner's carousel (the owner does that after deploy).
- Changing the drafting prompt version (v6) or the autopilot autofix (AE-0401/0407).
- Re-generating caption/blog after the field repair (they are built from the drafts before
  the review; slide-field rewrites do not change them materially).

## Acceptance Criteria

- [x] AC1: a blocked content gate sends ONLY the failing fields to the model, each with
  slide/locale/field path, current text, exact limit, problems, slide heading (+ PT source
  for EN); the answers replace only those fields and the gate re-validates.
- [x] AC2: at most 2 repair rounds, then stop with the remaining violations in
  `content_gate_validation`; nothing truncated; a failing model changes nothing.
- [x] AC3: a "Feedback para revisão" regeneration carries the owner's note AND the blocking
  violations; the repair loop runs after it; the history entry is `applied` only when the
  visible copy changed (`unchanged` otherwise).
- [x] AC4: the EN translation carries the PT `tldr_strip` / item lists; a residual
  `translation_shape_mismatch` is filled from PT and translated by the repair loop.
- [x] AC5: the editable EN column exposes every structured field PT has (TL;DR included);
  typing creates it on the EN payload; untouched slides are not sent as changed.
- [x] AC6: `**PT**` / `**EN**` / `**heading:**` scaffolding never reaches visible copy.
- [x] AC7: prompts in the registry (versioned YAML), Langfuse-traced, cost bounded.
- [x] AC8: regression fixture from the exported prod state (slides 1, 3, 6): the loop asks
  only for the 12 failing fields and the validator ends green with a limit-respecting model.
- [x] AC9: backend (except mutation, hotfix fast path) and frontend gates green locally (CI: see PR #151).

## Gherkin Scenarios

Full scenarios: `backend/tests/features/content_gate_repair_ae0430.feature` (A, B, C, E)
and `frontend/tests/features/content-review-en-structure-ae0430.feature` (D).

```gherkin
Feature: The content gate repairs only the failing fields (AE-0430)
  Scenario: An over-limit field is repaired in one round
  Scenario: Two rounds then stop with the violations shown
  Scenario: The repair never touches fields that pass
  Scenario: A failing model leaves the copy and the report as they were
  Scenario: The regression fixture from prod ends green
  Scenario: A revision request carries the blocking violations
  Scenario: A revision that changes nothing is not recorded as applied
  Scenario: A revision that changes the copy is recorded as applied
  Scenario: EN keeps the TL;DR strip of the intro
  Scenario: A residual shape mismatch is filled from PT and translated
  Scenario: Bold locale markers are parsed as sections, not copy
```

## Delta

### ADDED

- `backend/src/rag_backend/application/services/carousel/content_gate_repair.py`
- `backend/src/rag_backend/application/services/carousel/content_gate_repair_targets.py`
- `backend/src/rag_backend/application/services/carousel/content_gate_repair_flow.py`
- `backend/src/rag_backend/application/services/carousel/editorial_translation_structure.py`
- `backend/src/rag_backend/domain/constants/content_gate_repair.py`
- `backend/src/rag_backend/agents/prompts/carousel_gate_repair/{README.md,v1/field_repair.yaml}`
- `backend/src/rag_backend/agents/prompts/carousel/v8/{README.md,slide_translations.yaml}`
- `frontend/src/modules/editorial/workspace/lib/presentation-locale-mirror.ts`
- Features, tests and `backend/tests/fixtures/ae0430_carousel_5344_content_gate.json`.

### MODIFIED

- `phase_artifact_runner.py` (repairer config, violation note, repair hook, note status)
- `agents/carousel_editorial_orchestrator.py` (injects the fast-model repairer + Langfuse)
- `editorial_distribution_generation.py`, `carousel_template/prompts.py`,
  `domain/constants/carousel.py` (translation v8 + structure)
- `slide_scaffold_recovery.py` (bold locale sections, EN heading)
- `content_feedback_lifecycle.py`, `domain/constants/content_feedback.py` (`unchanged`)
- `frontend/.../content-phase-locale-fields.tsx`, `presentation-slide-resolution.ts`,
  `modules/editorial/index.ts`
- `docs/backend/slide-copy-validators.md`, `docs/backend/content-feedback-lifecycle.md`

### REMOVED

- None.

## Affected Areas

- Backend: carousel content phase (ensure, translation, scaffold recovery, feedback lifecycle).
- Frontend: content review manual editor (EN column).
- Database: none (state JSONB shapes unchanged; one new history status string).
- API: none (`phase_feedback_history[].status` may now be `unchanged`; the frontend does not
  branch on status).
- Prompts/LLM: new `carousel_gate_repair/v1/field_repair`; `carousel/v8/slide_translations`.
  At most 2 extra fast-model calls per blocked content ensure.
- Observability: logs `content_gate_repair_round|done|model_failed`; Langfuse via the
  injected runnable config.

## Dependencies

- Related: AE-0309 (fail-closed chain), AE-0401/0407 (autopilot autofix), AE-0405/0413
  (feedback lifecycle, manual fixes), AE-0414 (structured edits).

## Implementation Plan

1. Specs (two `.feature` files), prod fixture.
2. E (scaffold), C (translation structure + v8 prompt), A (targets, loop, flow, prompt), B
   (runner hook, violation note, `unchanged`), D (frontend mirror).
3. Tests per scenario; gates (hotfix fast path).

## QA Checklist

- [x] Security reviewed (no new input surface; model output only replaces requested paths)
- [x] Code quality reviewed (ruff/mypy strict, small modules)
- [x] Acceptance criteria validated (tests per scenario)
- [x] Edge cases tested (model failure, empty/unchanged answers, over-limit answers,
  unasked ids, item count mismatch, passing gate)
- [x] Orphan/unfinished code checked

## Progress Log

### 2026-10-19

Root causes traced on the exported state (repro: building the prod drafts reproduces the
`**PT**` leak; the loop on the prod slides asks exactly the 12 failing fields). Implemented
A–E with tests; docs updated.

## Files Touched

See Delta.

## Test Evidence

Hotfix fast path, each gate via `gate-capture.sh <scope>:<gate>`. DB gates SKIP locally (no
Postgres). The suite was run directly (5451 passed, 14 skipped, 93% total) and diff-cover
directly (98%). Python 3.11 compile/import OK. Mutation deferred to CI. Details:
`.agent/reports/AE-0430.dev-summary.md`.

GATES_JSON: {"pass":33,"fail":0,"skip":6,"results":[{"gate":"backend:format","status":"PASS"},{"gate":"backend:lint","status":"PASS"},{"gate":"backend:lint-diff","status":"PASS"},{"gate":"backend:blanket-ignore","status":"PASS"},{"gate":"backend:strict-diff","status":"PASS"},{"gate":"backend:type","status":"PASS"},{"gate":"backend:imports","status":"PASS"},{"gate":"backend:arch-ratchet","status":"PASS"},{"gate":"backend:docstrings","status":"PASS"},{"gate":"backend:dead-code","status":"PASS"},{"gate":"backend:inline-prompts","status":"PASS"},{"gate":"backend:redis-factory","status":"PASS"},{"gate":"backend:autopilot-env","status":"PASS"},{"gate":"backend:healthcheck-loopback","status":"PASS"},{"gate":"backend:bandit","status":"PASS"},{"gate":"backend:pip-audit","status":"PASS"},{"gate":"backend:integrity","status":"PASS"},{"gate":"backend:test","status":"SKIP"},{"gate":"backend:diff-cover","status":"SKIP"},{"gate":"backend:migrations","status":"SKIP"},{"gate":"backend:schema-drift","status":"SKIP"},{"gate":"frontend:lint","status":"PASS"},{"gate":"frontend:lint-changed","status":"PASS"},{"gate":"frontend:component-types","status":"PASS"},{"gate":"frontend:duplication","status":"PASS"},{"gate":"frontend:dead-code","status":"PASS"},{"gate":"frontend:typecheck","status":"PASS"},{"gate":"frontend:build","status":"PASS"},{"gate":"frontend:legacy-guard","status":"PASS"},{"gate":"frontend:legacy-inventory","status":"PASS"},{"gate":"frontend:format","status":"PASS"},{"gate":"frontend:security","status":"PASS"},{"gate":"frontend:integrity","status":"PASS"},{"gate":"frontend:test","status":"PASS"},{"gate":"frontend:schema-drift","status":"PASS"},{"gate":"frontend:duplication-tests","status":"PASS"},{"gate":"frontend:dead-files","status":"PASS"},{"gate":"backend:mutation","status":"SKIP"},{"gate":"frontend:mutation","status":"SKIP"}]}

## QA Report

Pending external QA.

## Decision Log

- **Field-level repair, not another slide re-draft**: the owner asked for a targeted step; a
  field-scoped request with the exact limit is cheaper, cannot regress passing fields, and
  is checkable (answers for unrequested ids are dropped).
- **Fill-from-PT before asking**: makes `translation_shape_mismatch` impossible to keep and
  turns it into a normal "translate this field" target.
- **`unchanged` history status** instead of keeping the note active: an active note would
  regenerate again on the next content entry; `unchanged` tells the owner the truth without
  a regeneration loop. The frontend does not branch on the status.
- **Write-back via `apply_localized_slide_edits`**: the same path as owner edits keeps
  drafts, EN translations, `presentation_validation` and `content_gate_validation` in step.
- **Repairer injected by the orchestrator (agents layer)**: no new application ->
  infrastructure import edge (import-linter baseline).
- **Prod re-run behaviour** (documented in the PR): the owner's next "Feedback para revisão"
  regenerates with the note plus the 12 violation lines, translates with v8 (TL;DR kept),
  and then repairs what is still blocked (≤2 fast-model calls). The history shows `applied`
  only if the copy changed. Whatever remains is listed and fixable by hand, EN TL;DR included.

- **Orchestrator review fix (PT TL;DR as EN)**: the translation fallback copied the PT
  TL;DR into EN and the language rules skipped `tldr_strip`, so the gate went green with a
  Portuguese EN TL;DR. Now `tldr_strip` is language-checked (`language_fields`,
  `translation_violations`) and an unanswered TL;DR stays absent, so the mismatch blocks
  and the repair loop translates it (retried in round 2 if the model skips it).

## Blockers

None.

## Final Summary

Pending QA / merge.

**Merged and closed (orchestrator, 2026-10-20).** Merged #151 (c9aac81, 2026-10-19), deployed. Scaffold leaks it missed (**PT-BR**, CTA creator:) were fixed in AE-0436.
