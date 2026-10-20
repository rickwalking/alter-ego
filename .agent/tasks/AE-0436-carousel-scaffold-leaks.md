# AE-0436 — Carousel scaffold label leaks (**PT-BR**, CTA creator:) and EN ** emphasis survive the content gate

Status: Dev Complete
Tier: T1
Priority: P1
Type: Bug
Area: Backend
Owner: worker (orchestrator-briefed, QA evidence 2026-10-20)
Agent Lane: developer → qa → release
Branch: feat/ae-0436-carousel-scaffold-leaks
Kanban Card: TBD
Created: 2026-10-20
Updated: 2026-10-20

## Goal

One label-scaffolding detector drives both the drafter parser (strip at the
source) and the content gate (a blocking, auto-repairable violation), so no
locale marker or field label — in any variant, wherever it sits in the text —
ever reaches visible slide copy. EN copy uses `<strong>…</strong>` emphasis
deterministically, and the prompt source that leaked "CTA creator:" is fixed.

## Problem

Prod evidence (QA 2026-10-19 run, carousel `7acaf967`, read-only report
`~/alter-ego-qa/2026-10-19-qa-full/REPORT.md`):

- **F-03 (major):** slide 5 PT body shipped `"**PT-BR**\nInovação não exige
  **bilhões**…"` after auto-repair; the content gate reported blocking=false.
  The AE-0430 (#151) parser only recognises `**PT**` / `**EN**` locale markers,
  not the `**PT-BR**` variant.
- **F-04 (major):** slide 7 EN body ended with `"**CTA creator: radar IA.**"` —
  a field label leaked into visible copy; the gate did not flag it.
- **F-09 (minor):** EN columns keep PT-style `**…**` emphasis (slides 1/3/4)
  instead of `<strong>`; the UI only hints ("Converter ênfase"), nothing flags
  or auto-fixes it (AE-0366/AE-0403 convention: PT `**`, EN `<strong>`).
- Hand-checked on carousel `5344b6c6` (2026-10-19): existing drafts with
  `"**PT** ** **"` and `"PT: Heading:"` garbage are not flagged by the gate;
  AE-0430 strips only at the source for NEW drafts.

### Root causes (file:line on `origin/main`, 4f811e6fd2)

1. **Locale-marker parser too narrow (F-03).** `slide_scaffold_recovery.py:56-60`
   matches `## X` and bold `PT|EN` only; `**PT-BR**` (and `PT: Heading:` plain
   variants) fall through `strip_scaffold_labels` (`:109-119`) into the body.
2. **No gate rule for label scaffolding (F-03/F-04).**
   `presentation_validation_fields.py:33-36` (`contains_drafting_scaffold`)
   matches only `SLIDE N|TITLE|BODY|KEY POINTS:` labels, so `**PT-BR**`,
   `**CTA creator:**`, `PT:`, `Heading:` never fire `drafting_scaffold_present`
   (a blocker in v4/pov). The repair `_repair_scaffold_fields`
   (`presentation_copy_repair.py:192-205`) only strips heading/body, and the
   stripper it calls only handles line-start prefixes.
3. **Prompt source leaks the label (F-04).** `render_presentation_policy_context`
   (`presentation_policy.py:106-150`) renders the raw schema field names into
   the drafter prompt ("Copy budgets: - cta_creator_name: max 60 characters");
   the model echoed `cta_creator_name` as "**CTA creator: radar IA.**" in the
   closing slide's body.
4. **No per-locale emphasis rule (F-09).** The translator (v8) keeps whatever
   emphasis the PT source carries — `**` — and nothing converts or flags it.
   `emphasis_markup_invalid` (AE-0366) only validates `<strong>` balance, so
   EN `**…**` passes; the frontend hint is the only signal.

## Scope

- ONE shared, data-driven label-scaffolding detector
  (`application/services/carousel/label_scaffolding.py`): locale markers in any
  variant (PT, PT-BR, pt_BR, EN, EN-US, bold or plain, with or without colon)
  and field labels (Heading, Body, Title, Subtitle, CTA, CTA creator, Summary,
  TL;DR, Key points, …), detected wherever they sit in the text. Used by BOTH:
  - the drafter parser strip (`slide_scaffold_recovery.py` — section split and
    `strip_scaffold_labels`, extended to the new variants), and
  - the content gate: `contains_drafting_scaffold` →
    `drafting_scaffold_present` (already a blocker in v4/pov, already repaired
    deterministically by `_repair_scaffold_fields` and per-field by the AE-0430
    gate repair loop).
- The deterministic scaffold repair also strips the labels on item texts (not
  only heading/body).
- The prompt source fix: `render_presentation_policy_context` renders
  human-readable budget labels ("owner name on the CTA card"), never raw
  snake_case schema field names, and says the names are schema identifiers,
  never visible copy. The v4/pov `drafting_scaffold_forbidden` rule summary
  names locale markers and field labels explicitly.
- Emphasis per locale (AE-0403/AE-0414 convention): PT `**…**`, EN
  `<strong>…</strong>`.
  - Deterministic normalization at write time: PT `<strong>x</strong>` →
    `**x**`, EN `**x**` → `<strong>x</strong>` in the review repair
    (`deterministic_repair_slide_payload`) and the autofix plan (`_polish`),
    gated on the policy declaring the new rule.
  - New gate rule `emphasis_markup_locale_mismatch` (blocker) in
    `hero_lower_third_v4` and `pov_hook_v1`, checked on every visible field.
  - The translation request converts PT emphasis to `<strong>` so the model's
    "keep every `<strong>` tag" instruction applies; the translation prompt
    says EN emphasis is `<strong>`, never `**` (new version `carousel/v9`,
    v8 kept for rollback).
- Fixtures from the real prod strings above.

## Non-Goals

- Changing v1–v3 policy semantics (the new rule only exists in v4/pov).
- Rewriting unbalanced emphasis (that is `emphasis_unbalanced`, unchanged).
- Retroactively rewriting stored copy outside the write/review/autofix paths.
- Frontend changes: the mismatch hint/converter already exists (AE-0414).

## Acceptance Criteria

- [x] AC1: `**PT-BR**` (and PT_BR / pt_BR / EN / EN-US variants, bold or plain,
  with or without colon) and `Heading:` / `Body:` / `CTA creator:` / `CTA:` /
  `Summary:` / `TL;DR:` labels are detected anywhere in the text by one
  shared detector.
- [x] AC2: the drafter parser splits/strips the new variants (prod fixtures):
  `"**PT-BR**\nInovação não exige **bilhões**…"` builds a PT body that starts
  with "Inovação…"; `"**PT** ** **"` and `"PT: Heading:"` leave no marker.
- [x] AC3: the content gate flags every leak above as a blocker
  (`drafting_scaffold_present`) on the exact field (heading, body, item),
  PT and EN, and the deterministic repair strips it; the re-validated gate
  turns green.
- [x] AC4: the rendered policy context contains no raw snake_case budget field
  names (`cta_creator_name`, `closing_action_title`, …) and tells the model
  field names are never visible copy.
- [x] AC5: EN `**x**` normalizes to `<strong>x</strong>` and PT
  `<strong>x</strong>` to `**x**` at write time (review repair + autofix),
  deterministically; the gate flags a mismatch when it survives
  (`emphasis_markup_locale_mismatch`, blocker, v4/pov).
- [x] AC6: the EN translation request sends PT emphasis as `<strong>` and the
  v9 translation prompt forbids `**` in EN copy.
- [x] AC7: rule-fires tests for the new gate rule on seeded violations; the
  real prod strings are fixtures; backend gates (except mutation, hotfix fast
  path) green locally; Python 3.11 import check; CI green (pending).

## Gherkin Scenarios

`backend/tests/features/carousel_label_scaffolding_ae0436.feature`:
- Locale markers in every variant are detected anywhere in copy
- Field labels (Heading/Body/CTA creator/CTA/Summary/TL;DR) are detected anywhere
- The drafter strip removes PT-BR markers and PT: Heading: garbage from prod drafts
- A **PT-BR** body draft builds a clean PT payload
- The content gate flags **PT-BR**, CTA creator: and PT: Heading: as blockers
- The deterministic repair strips the labels and the gate turns green
- Item texts are label-checked and stripped too
- EN **x** normalizes to <strong>x</strong>; PT <strong>x</strong> to **x**
- A surviving mismatch is a blocker; the policy context never exposes field names

## Affected Areas

- [x] Backend
- [ ] Frontend
- [x] Tests

## Dependencies

None. Parallel workers AE-0435..AE-0440: shared files are touched minimally
(contract YAMLs, presentation validators).

## Progress Log

### 2026-10-20

Root causes traced (shared detector, gate, policy-context leak, emphasis
convention). Gherkin + 45 tests on the real prod strings. The AE-0430 prod
fixture now correctly reveals the 4 leaks it always carried (slide 1
`**PT**`, slide 4 `**PT** ** **` / `PT:\nHeading:`, slide 3 EN `**…**`);
its tests and PROD_ANSWERS were extended for them. Full local gate run green
except mutation (killed locally, deferred to CI — hotfix fast path). PR open.

## Files Touched

### ADDED

- `backend/src/rag_backend/application/services/carousel/label_scaffolding.py`
- `backend/src/rag_backend/agents/prompts/carousel/v9/{README.md,slide_translations.yaml}`
- `backend/tests/features/carousel_label_scaffolding_ae0436.feature`
- `backend/tests/unit/application/test_label_scaffolding_ae0436.py`
- `.agent/tasks/AE-0436-carousel-scaffold-leaks.md`

### MODIFIED

- `backend/src/rag_backend/application/services/carousel/slide_scaffold_recovery.py`
  (locale variants + shared strip)
- `backend/src/rag_backend/application/services/carousel/presentation_validation_fields.py`
  (gate detector + message)
- `backend/src/rag_backend/application/services/carousel/presentation_copy_rules.py`
  (emphasis locale rule)
- `backend/src/rag_backend/application/services/carousel/copy_hygiene_text.py`
  (`emphasis_locale_detail`)
- `backend/src/rag_backend/application/services/carousel/owner_autofix_text.py`
  (`normalize_emphasis`)
- `backend/src/rag_backend/application/services/carousel/owner_autofix_plan.py`
  (write-time normalization in `_polish`)
- `backend/src/rag_backend/application/services/carousel/presentation_copy_repair.py`
  (deterministic repair: items + emphasis)
- `backend/src/rag_backend/application/services/carousel/editorial_distribution_generation.py`
  (translation payload carries `<strong>`)
- `backend/src/rag_backend/application/services/carousel/presentation_policy.py`
  (human budget labels + schema note)
- `backend/src/rag_backend/domain/constants/carousel_presentation.py`
  (new violation constant)
- `backend/src/rag_backend/domain/constants/carousel.py`
  (`CAROUSEL_TRANSLATION_PROMPT_VERSION` → v9)
- `backend/src/rag_backend/agents/skills/carousel-pipeline/contracts/{hero_lower_third_v4,pov_hook_v1}.yaml`
  (severity + rule summary)
- `backend/tests/unit/application/content_gate_repair_fixtures_ae0430.py`,
  `backend/tests/unit/application/test_content_gate_repair_ae0430.py`
  (fixture now reveals its 4 real leaks; answers extended)
- `docs/backend/slide-copy-validators.md`

## Test Evidence

Hotfix fast path. Local Postgres: `postgres:16-alpine` container `ae0436-pg`
on `127.0.0.1:55436` (`postgresql+asyncpg://test:test@127.0.0.1:55436/rag_test`).
Python 3.13 venv (baseline green); 3.11 import check ran on a 3.11 venv (OK).

- New tests: `test_label_scaffolding_ae0436.py` — 45 passed (all scenarios of
  `carousel_label_scaffolding_ae0436.feature`); the AE-0430 fixture tests
  extended for the 4 leaks the stricter gate now reveals — 18 passed.
- Full unit suite (no DB): 5135 passed, 1 skipped.
- `bash scripts/ci/gate-capture.sh backend` (full run, DATABASE_URL set):
  22 PASS, 0 SKIP, 1 FAIL. The single FAIL is `backend:mutation` — the
  forbidden local mutation run was killed seconds after mutmut started
  (score line is the kill, not a result); mutation is deferred to CI.
  `backend:test` (6024 passed) and `backend:diff-cover` PASS.
- Python 3.11 import check: OK (prod image is `python:3.11-slim`).
- `.agent` ticket validation: all tickets OK.

GATES_JSON: {"pass":22,"fail":1,"skip":0,"results":[{"gate":"backend:format","status":"PASS"},{"gate":"backend:lint","status":"PASS"},{"gate":"backend:lint-diff","status":"PASS"},{"gate":"backend:blanket-ignore","status":"PASS"},{"gate":"backend:strict-diff","status":"PASS"},{"gate":"backend:type","status":"PASS"},{"gate":"backend:imports","status":"PASS"},{"gate":"backend:arch-ratchet","status":"PASS"},{"gate":"backend:docstrings","status":"PASS"},{"gate":"backend:dead-code","status":"PASS"},{"gate":"backend:inline-prompts","status":"PASS"},{"gate":"backend:blog-v1-dead-code","status":"PASS"},{"gate":"backend:redis-factory","status":"PASS"},{"gate":"backend:autopilot-env","status":"PASS"},{"gate":"backend:healthcheck-loopback","status":"PASS"},{"gate":"backend:bandit","status":"PASS"},{"gate":"backend:pip-audit","status":"PASS"},{"gate":"backend:integrity","status":"PASS"},{"gate":"backend:test","status":"PASS"},{"gate":"backend:diff-cover","status":"PASS"},{"gate":"backend:migrations","status":"PASS"},{"gate":"backend:schema-drift","status":"PASS"},{"gate":"backend:mutation","status":"FAIL"}]}

## QA Report

Pending.

## Decision Log

- **Reuse `drafting_scaffold_present`** instead of a new code for label leaks:
  it is the exact semantic, already a blocker in v4/pov, and already wired to
  the deterministic repair and the AE-0430 per-field LLM repair. A new code
  would duplicate plumbing.
- **New `emphasis_markup_locale_mismatch` (blocker)** instead of upgrading the
  frontend hint: the convention is objective and deterministically reparable,
  so a blocker that auto-fixes at write time matches the other copy-hygiene
  blockers.
- **`carousel/v9` translation prompt** (never edit v8, prompt-versioning rule).
- **Human budget labels in the policy context** (code), not a content-prompt
  version bump: the leak came from the rendered policy context, so the fix
  lives next to the rendering, and every prompt version that renders it is
  fixed at once.
- **AE-0430 fixture tests updated, not weakened**: the prod export of 5344b6c6
  really contains the leaks the QA hand-noted (slide 1 `**PT**`, slide 4
  `**PT** ** **` / `PT:\nHeading:`, slide 3 EN `**…**`); the stricter gate now
  finds them, so the fake repairer answers those 4 fields with clean copy and
  the fixture test asserts the stored 12 violations plus the 4 new ones.

## Blockers

None.
