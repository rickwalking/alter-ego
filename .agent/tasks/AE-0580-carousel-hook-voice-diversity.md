# AE-0580 — Carousel hooks repeat the same openings (voice diversity)

Status: In Development
Tier: T1
Priority: High
Type: Bug
Area: Backend
Owner: Pedro Marins
Branch: hotfix/ae-0579-voice-diversity
Created: 2026-10-31
Updated: 2026-10-31

## Goal

Generated POV carousel hooks stop repeating the same formulas and openings
("Opinião impopular: ...", "o que eu faço ...") across carousels while keeping
Pedro's persona voice and the voice gate untouched.

## Problem

Every POV outline renders the same hook prompt with no memory of what previous
carousels opened with, and slide 1 always takes candidate #1, so the model
converges on the same openings carousel after carousel.

## Scope

- New `carousel_pov/v2/hook.yaml` and `carousel_pov_news/v2/hook.yaml` prompt
  versions (v1 is never edited): they take the owner's recent slide-1 openings
  and instruct the model not to reuse those openings or their formulas.
- Recent openings are read from the DB (`carousel_slides` slide 1 of the
  owner's recent carousels, current project excluded).
- The chosen hook rotates deterministically across the candidates (seeded by
  the project id) instead of always taking the first candidate.
- Tests + `.feature` file.

## Non-Goals

- Do not loosen the persona voice gate or scoring.
- Do not edit v1 prompt files.
- Do not change Radar IA hooks beyond the shared exclusion guidance (unchanged).
- Do not refactor unrelated code.

## Acceptance Criteria

- [ ] The v2 hook prompt lists the owner's recent openings and forbids reusing
      them and their formulas; without recent openings the block is omitted.
- [ ] N consecutive generations with the same candidate list do not reuse the
      same hook (deterministic rotation by project seed).
- [ ] The owner's saved hook still wins over the rotation.
- [ ] Recent openings come from the DB: owner's carousels only, current
      project excluded, capped, newest first.
- [ ] Backend gates green (hotfix fast path: all gates except local mutation).

## Repro Steps

1. Generate several POV carousels in a row.
2. Slide 1 openings repeat the same formulas ("Opinião impopular: ...").

## Affected Areas

- [x] Backend
- [ ] Frontend
- [x] Tests

## Dependencies

None.

## Progress Log

### 2026-10-31

Ticket created (hotfix, Pedro 2026-10-31). Implemented: v2 hook prompts
(carousel_pov, carousel_pov_news) with the recent-openings exclusion block,
domain `RecentHookReader` port + `SqlRecentHookReader`, deterministic hook
rotation seeded by the project id, wired through `ModeOutlineRequest` and the
phase artifact runner. Renumbered AE-0579 -> AE-0580 (id taken by PR #315).

## Files Touched

- backend/src/rag_backend/agents/prompts/carousel_pov/v2/ (hook.yaml, README)
- backend/src/rag_backend/agents/prompts/carousel_pov_news/v2/ (hook.yaml, README)
- backend/src/rag_backend/agents/pov_outline_mixin.py
- backend/src/rag_backend/agents/carousel_editorial_orchestrator.py
- backend/src/rag_backend/application/services/carousel/recent_hooks.py (new)
- backend/src/rag_backend/application/services/carousel/outline_by_mode.py
- backend/src/rag_backend/application/services/carousel/phase_artifact_runner.py
- backend/src/rag_backend/application/services/carousel/editorial_workflow_generators.py
- backend/src/rag_backend/domain/constants/pov_prompts.py
- backend/src/rag_backend/domain/models/pov_prompts.py
- backend/src/rag_backend/domain/protocols/recent_hooks.py (new)
- backend/src/rag_backend/infrastructure/database/carousel_recent_hooks.py (new)
- backend/tests/features/carousel_pov_hook_diversity_ae0580.feature (new)
- backend/tests/unit/application/test_pov_hook_diversity_ae0580.py (new)
- backend/tests/unit/application/test_pov_prompts_ae0375.py
- backend/tests/unit/agents/test_carousel_editorial_orchestrator.py

## Test Evidence

- 12 new unit tests (prompt exclusion block on/off, v2 wiring, rotation
  covers all candidates without repeats, deterministic per project, saved
  hook wins, owner-scoped recent openings newest-first with cap and current
  project excluded, no-reader degradation).
- backend gates green locally (hotfix fast path): format, lint, lint-diff,
  blanket-ignore, strict-diff, type, imports, arch-ratchet, docstrings,
  dead-code, inline-prompts, gherkin-refs, comments, blog-v1-dead-code,
  redis-factory, autopilot-env, healthcheck-loopback, openapi-fresh, bandit,
  pip-audit, integrity, duplication, test (7896 passed), diff-cover,
  migrations, schema-drift. mutation: deferred to CI (hotfix fast path).
- Python 3.11 py_compile on all changed source files (prod image is 3.11).

## QA Report

Pending.

## Blockers

None.
