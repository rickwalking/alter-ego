# AE-0408 — Follow CTA no longer promises a Tuesday and Thursday schedule

Status: In Development
Tier: T1
Priority: High
Type: Bug
Area: Backend
Owner: Claude (orchestrator)
Branch: fix/ae-0408-cta-no-weekdays
Created: 2026-10-17
Updated: 2026-10-17

## Goal

The follow CTA slide no longer says "toda terça e quinta" / "every Tuesday and Thursday".

## Problem

Owner final-review feedback on carousel be190a0c (pov_news, autopilot run f88bc343, 2026-10-17
03:48Z): "At the final slide, revoke the 'toda terça e quinta'". The phrase is not model copy: it
is the hard-coded `follow` CTA template (`domain/constants/carousel_cta.py`, AE-0372), so a content
rework cannot remove it and every follow-goal carousel promises a fixed weekday schedule.

## Scope

- `CTA_COPY_PT[follow]` → "Siga {handle}: eu traduzo IA em decisões reais."
- `CTA_COPY_EN[follow]` → "Follow {handle}: I turn AI into real decisions."
- Tests, the AE-0372 feature file and the growth-plan doc updated; a regression test that no CTA
  copy names a weekday.

## Non-Goals

- Do not change the POV publish slots (`pov_schedule.py` keeps Tuesday/Thursday 12:00).
- Do not change the send/comment CTA variants.

## Acceptance Criteria

- [x] The follow CTA (PT and EN) renders without any weekday.
- [x] No CTA copy variant names a weekday (regression test).
- [x] Existing CTA tests pass with the new copy.

## Repro Steps

1. Render any carousel whose CTA goal is `follow`.
2. The CTA slide reads "Siga @pedromarins.ai: toda terça e quinta eu traduzo IA em decisões reais."

## Affected Areas

- [x] Backend
- [ ] Frontend
- [x] Tests

## Dependencies

None.

## Progress Log

### 2026-10-17 04:00

Ticket created from the owner's final-review feedback; copy, tests and docs updated.

## Files Touched

- backend/src/rag_backend/domain/constants/carousel_cta.py
- backend/tests/features/radar_ia_quick_fixes.feature
- backend/tests/unit/application/strategies/test_cta.py
- backend/tests/unit/application/strategies/test_radar_ia_quick_fixes_ae0372.py
- backend/tests/unit/application/test_carousel_template_builder.py
- backend/tests/unit/domain/test_carousel_cta_copy_ae0408.py
- docs/architecture/instagram-growth-pov-mode.md

## Test Evidence

Pending.

## QA Report

Pending.

## Blockers

None.
