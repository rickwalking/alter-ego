# AE-0362 — Autopilot outline and images gates expect the pipeline's 7-slide count

Status: Intake
Tier: T1
Priority: P0
Type: Bugfix
Area: backend
Owner: Claude Code (claude-opus-5-5)
Branch: fix/ae-0362-autopilot-slide-count
Created: 2026-10-14
Updated: 2026-10-14
Parent: AE-0348

## Goal

An autopilot run with a correct 7-slide outline and 7 generated hero images passes the outline
and images gates instead of escalating.

## Problem

Prod escalation 2026-10-14. The first real autopilot run (carousel
`8e350d6e-78fc-436c-ab95-bed02535198b`, "Gemini 4 Argon chegou") escalated at the outline gate
with `outline_slide_count_mismatch`. The outline had 7 items, which is what the pipeline always
builds: the outline agent sizes it from the presentation contract `slide_count: 7`
(`hero_lower_third_v1/v2.yaml`), and `CAROUSEL_DEFAULT_SLIDES_CONFIG` is also 7. The autopilot
created the project with a stale `AUTOPILOT_SLIDES_CONFIG` of 6 slides, and the gate compared
against `slides_in_config(project.slides_config)` = 6.

The images gate had the same count problem, plus a second assumption that could never hold: it
required every `image_assets` file to be 1080x1350. `image_assets` are the raw hero images
(OpenAI `gpt-image` renders 1536x1024); the 1080x1350 slides are only composed at finalize. So
the images gate would have escalated every real run too.

## Scope

- Create autopilot projects with `CAROUSEL_DEFAULT_SLIDES_CONFIG` (7). Delete the stale
  `AUTOPILOT_SLIDES_CONFIG`.
- Expected slide count = the project's presentation contract `slide_count` (the same source the
  outline agent uses), falling back to `slides_config` only if the contract cannot be loaded.
  Verified `slide_count_from_config("7_slides") == 7`.
- Images gate: one present JPEG with a decodable size per expected slide. Drop the 1080x1350
  requirement, which applies to composed slides, not hero images.
- Regression tests + Gherkin scenarios in `backend/tests/features/autopilot_runner.feature`.
- Doc: `docs/architecture/grokbot-autopilot.md` gate list.

## Non-Goals

- Do not refactor unrelated code.
- No DB migration (prod deploys don't run Alembic). Existing rows are not rewritten; the
  contract-based count already fixes projects created with the old 6-slide config.
- Re-driving the escalated prod run is an owner action, not part of this fix.

## Acceptance Criteria

- [x] Autopilot-created projects use `CAROUSEL_DEFAULT_SLIDES_CONFIG`; `AUTOPILOT_SLIDES_CONFIG`
  is gone.
- [x] An outline of 7 items for an autopilot-created project → APPROVE.
- [x] 7 hero JPEGs (1536x1024) for an autopilot-created project → APPROVE at the images gate.
- [x] A project whose `slides_config` is `"7_slides"` → expected count 7.
- [x] A project with the stale 6-slide config but a v2 contract → expected count 7.
- [x] A real mismatch still revises: 5 outline items → REVISE `outline_slide_count_mismatch`;
  6 images, a missing file, a non-JPEG or a zero dimension → REVISE `image_assets_invalid`.
- [x] Unreadable contract falls back to `slides_config`.
- [x] Python 3.11 import check: every `rag_backend` module imports.

## Repro Steps

1. Queue an autopilot topic; let the runner create and start the carousel.
2. The outline phase produces 7 items (contract `slide_count: 7`).
3. Before the fix: the outline gate compares 7 against `slides_in_config` of the 6-slide config
   and escalates with `outline_slide_count_mismatch` after two revises.

## Affected Areas

- [x] Backend
- [ ] Frontend
- [x] Tests

## Dependencies

None.

## Gate sweep (other policy assumptions checked against the real pipeline)

- research: findings are `{"source", "key_points", "summary"}` from `synthesize_research`; the
  gate's content/summary/key_points check matches. Count = scout URLs (1–8) + up to 3 web hits
  when `research_enrichment_enabled`; ≥3 is reachable but not guaranteed when enrichment is off
  and the scout sends <3 URLs (a real data condition, not an impossible check). Not changed.
- content: `persona_scores` values are `PersonaAgent.evaluate_match` dicts with a float
  `overall`; the snapshot reads `overall` (missing → 0, like the engine). Matches.
- design: `presentation_validation` `blocking`/`violations` shape matches the engine. Matches.
- images: count and 1080x1350 size assumptions fixed here.

## Progress Log

### 2026-10-14

Ticket created from the prod escalation. Test-first: `test_slide_count_ae0362.py` failed (7 of
12) on the old code, then the fix landed. Gates run once at the end; see the dev summary.

## Files Touched

- `backend/src/rag_backend/modules/autopilot/constants.py`
- `backend/src/rag_backend/modules/autopilot/infrastructure/editorial_driver.py`
- `backend/src/rag_backend/modules/autopilot/domain/policy.py`
- `backend/src/rag_backend/modules/editorial/infrastructure/carousel_automation.py`
- `backend/tests/unit/modules/autopilot/test_slide_count_ae0362.py` (new)
- `backend/tests/unit/modules/autopilot/test_gate_policy.py`
- `backend/tests/integration/test_autopilot_runner_start.py`
- `backend/tests/features/autopilot_runner.feature`
- `docs/architecture/grokbot-autopilot.md`

## Test Evidence

See `.agent/reports/AE-0362.dev-summary.md` (GATES_JSON line).

## QA Report

Pending.

## Blockers

None.
