# AE-0437 — Closing actions are never generated or repaired, the editor cannot add them, and revisions rewrite slides they were not asked to touch

Status: In Development
Tier: T2
Priority: P1
Type: Bug
Area: Fullstack
Owner: worker (orchestrator-briefed, QA evidence 2026-10-19)
Agent Lane: developer → qa → release
Branch: feat/ae-0437-closing-actions-scoped-revisions
Kanban Card: TBD
Created: 2026-10-20
Updated: 2026-10-20

## Goal

A closing slide always ends up with 3 structured `actions` (drafted, kept under the
right key, filled by the repairs, or added by hand), a revision changes only the
slides it names, and an EN field never keeps Portuguese text a repair produced.

## Problem

Prod QA 2026-10-19 (`~/alter-ego-qa/2026-10-19-qa-full/REPORT.md`), carousel
`7acaf967` (`hero_lower_third_v4`):

- **F-06 (major):** `closing_actions_missing` on slide 6 PT/EN survived the initial
  generation, the auto-repair, a retry and revision 1. "Corrigir problemas
  automaticamente" was a no-op (same `validated_at`). The manual editor showed
  `Campo estruturado: actions []` with no way to add an item, so the owner was stuck.
- **F-10 (minor):** revision 1, asked to change only slides 2 and 6, rewrote slides
  1, 3 and 7; slide 3 lost its 3 features.

Carousel `5344b6c6` (2026-10-19, by hand, `~/alter-ego-qa/2026-10-19-carousel-5344/`):
after a correction the closing items were stored under `features`; the UI hid
"Enviar correções manuais" when the server was no longer blocking, so a late EN
TL;DR edit could only be sent by approving; the EN TL;DR showed a Portuguese
sentence after AE-0430.

### Root causes (file:line on `origin/main` 4f811e6fd2)

1. **The drafter is told to use `features`.** `carousel-pipeline/phases/content/SKILL.md:27`
   ("checklist (`features` array)") and `_shared/content-contracts.md:69,85` ("must
   return `features: [...]` on the closing slide") contradict the contract
   (`hero_lower_third_v4.yaml:204`, 3 `actions`). `localized_slide_builder._build_locale_payload`
   copies whichever key the model used.
2. **Rows store closing actions as `features` and never map them back.**
   `editorial_distribution_slide._structured_from_presentation:82-84` writes
   `actions` into the row's `features` column (there is no `actions` column);
   `carousel_repair_projection._locale_payload` (used by the owner autofix and the
   manual slide-edit service) reads them back as `features`, and the autofix then
   writes that payload into the checkpoint (the 5344 key swap).
3. **No repair can create actions.** `owner_autofix_plan._fill` filled content
   features and summary points from the outline but never closing actions; the
   AE-0430 gate repair only rewrites fields that exist, so `actions: []` stays empty
   (and so does `summary_points: []`).
4. **A revision regenerates the whole deck.** `phase_artifact_runner._ensure_content_artifacts`
   re-drafts every outline entry on any revision note and replaces `slide_drafts` and
   `localized_slides`; the "change only these slides" scope existed only in the prompt.
5. **EN copy accepted in Portuguese.** The prod checkpoint of 5344 (`localized_slides`
   v16, read-only) holds EN `tldr_strip` = "Eu olho para o computador, não para a demo"
   (Portuguese for the EN body's first sentence): `content_gate_repair_targets.apply_fixes`
   accepted any answer for an EN target, and a PT structure copied into EN for
   translation stayed in EN when no translation came back.
6. **Editor:** an empty item list is not a "list" (`isPresentationStructuredItemList`
   needs length > 0), so it fell through to a read-only raw extra; the list shown was
   the first non-empty one in the order summary_points, features, actions (a closing
   EN `features` hid the `actions`); the manual-fix footer was gated on server
   blocking only.

## Scope

- Backend
  - `closing_actions.restore_closing_actions`: a closing payload's `features` become
    `actions` (when it has none) in the localized builder and the row read-back.
  - `structure_fill` (shared by the owner autofix and the gate repair): fills a
    closing slide's 3 actions from its outline key points (closing budgets 30/90,
    contract icons) and moves swapped closing `features` back to `actions`; summary
    points and features as before. The gate repair gets the outline from the
    workflow state.
  - Gate repair: an EN answer that `looks_portuguese` is dropped; a PT structure copied
    into EN that nobody translated is taken out of EN again.
  - `revision_scope`: when the owner's revision notes name slides, only those slides
    plus the slides the gate blocks are drafted (`SlideDraftGenerationParams.only_slides`),
    fresh drafts replace only their slides, and every other slide gets its stored
    localized copy back (`apply_localized_slide_edits`, so drafts, translations and
    both reports stay in step). A note naming no slide still rewrites the deck.
  - Drafting instructions: the closing slide returns `actions` (3 items).
- Frontend
  - Each slide type edits its own list (`summary_points` / `actions` / `features`),
    offered even when empty, with "Adicionar …" and "Remover …" buttons (max 4 items).
    Add/remove applies to PT and EN at the same position (the gate needs PT/EN parity
    and the AE-0430 mirror would otherwise pad a removed slot straight back).
  - An empty item list is never shown as a raw "Campo estruturado" extra.
  - "Enviar correções manuais" shows whenever there are unsaved edits, also when the
    server is not blocking (the blocking-slides hint only when it is).

## Non-Goals

- Changing the closing rule (`closing_actions_missing` still counts actions + features,
  so existing decks with closing `features` keep passing and now read back as actions).
- Rewriting existing prod rows (no data migration; the next autofix/repair/edit reads
  closing rows back as `actions`).
- Label/scaffolding parsing and label gate rules (AE-0436).

## Acceptance Criteria

- [x] AC1: the drafting instructions ask for closing `actions`; a closing checklist
  drafted or stored as `features` is read back as `actions` (builder + row read-back).
- [x] AC2: the owner autofix fills missing closing actions from the outline (or moves
  swapped features back) in PT, mirrors them to EN for translation, and invents
  nothing with too few key points.
- [x] AC3: the content gate repair fills missing closing actions and summary points
  from the outline and asks the model only for the EN translations; the gate stops
  blocking on them.
- [x] AC4: an EN repair answer in Portuguese is dropped; an untranslated PT copy is
  taken out of EN.
- [x] AC5: a revision that names slides re-drafts only those (+ blocked) slides; every
  other slide keeps its stored localized copy and draft; a general note still
  rewrites the deck; a first draft is never scoped.
- [x] AC6: the editor offers add/remove slots for summary points, features and closing
  actions (empty lists included), in both locales; a closing slide edits `actions`.
- [x] AC7: unsaved edits can be submitted without approving when the server is not
  blocking.
- [ ] AC8: backend + frontend gates (except local mutation) green locally; CI green.

## Gherkin Scenarios

- `backend/tests/features/closing_actions_scoped_revisions_ae0437.feature`
- `frontend/tests/features/content-review-item-slots-ae0437.feature`

## Affected Areas

- [x] Backend
- [x] Frontend
- [x] Tests

## Dependencies

None. Shares `owner_autofix_plan.py` with AE-0436 (AE-0436 edits `_polish`; this
ticket moves `_fill`/`_mirror_fill` into `structure_fill.py`, `_polish` untouched).

## Progress Log

### 2026-10-20

Root causes traced (code + prod read-only checkpoint query), backend + frontend fix,
Gherkin + tests.

## Files Touched

- `backend/src/rag_backend/application/services/carousel/{closing_actions,structure_fill,revision_scope}.py` (new)
- `backend/src/rag_backend/application/services/carousel/{owner_autofix_plan,owner_autofix_fill,owner_autofix_source,content_gate_repair,content_gate_repair_targets,content_gate_repair_flow,carousel_repair_projection,localized_slide_builder,editorial_workflow_generators,phase_artifact_runner}.py`
- `backend/src/rag_backend/domain/constants/carousel_autofix.py`
- `backend/src/rag_backend/agents/skills/carousel-pipeline/{phases/content/SKILL.md,_shared/content-contracts.md}`
- `backend/tests/features/closing_actions_scoped_revisions_ae0437.feature`
- `backend/tests/unit/application/{test_closing_actions_ae0437,test_revision_scope_ae0437}.py`,
  `backend/tests/unit/agents/test_scoped_revision_ae0437.py`,
  `backend/tests/unit/application/test_content_gate_repair_ae0430.py` (one test now
  translates the EN copies it expects to stay; see AC4)
- `frontend/src/modules/editorial/workspace/lib/presentation-structured-lists.ts` (new) + test
- `frontend/src/modules/editorial/workspace/lib/presentation-review-utils.ts`, `frontend/src/modules/editorial/index.ts`
- `frontend/src/app/dashboard/create/workspace/phase-review/content-phase-{review,locale-fields,structured-fields}.tsx`
  + `content-phase-review.item-slots.test.tsx`
- `frontend/src/constants/editorial-workflow.ts`, `frontend/src/i18n/locales/{pt,en}.json`
- `frontend/tests/features/content-review-item-slots-ae0437.feature`

## Test Evidence

Local gates, each run on its own (`bash scripts/ci/gates.sh <scope>:<gate>`) with a private
Postgres (`DATABASE_URL` set), 2026-10-20:

- backend: format, lint, lint-diff, blanket-ignore, strict-diff, type, imports, arch-ratchet,
  docstrings, dead-code, inline-prompts, redis-factory, autopilot-env, healthcheck-loopback,
  bandit, pip-audit, integrity, **test (6016 passed, 2 skipped)**, **diff-cover (98%)**,
  migrations, schema-drift = PASS.
- frontend: lint, lint-changed, component-types, duplication, dead-code, typecheck, build,
  legacy-guard, legacy-inventory, format, security, integrity, test, schema-drift,
  duplication-tests, dead-files = PASS.
- mutation (backend + frontend): not run locally (shared machine, OOM rule); CI is the
  source of truth.
- New tests: backend 36 (`test_closing_actions_ae0437.py` 15, `test_revision_scope_ae0437.py`
  18, `test_scoped_revision_ae0437.py` 3); frontend 13 (`presentation-structured-lists.test.ts`
  8, `content-phase-review.item-slots.test.tsx` 5).

```
GATES_JSON: {"pass":37,"fail":0,"skip":0,"note":"every backend+frontend gate except mutation (deferred to CI)"}
```

## QA Report

Pending.

## Blockers

None.
