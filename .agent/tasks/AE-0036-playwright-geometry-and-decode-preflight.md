# AE-0036 — Playwright Geometry and Decode Preflight

Status: Ready to Merge
Tier: T2
Priority: Critical
Type: Feature
Area: Backend/Export
Owner: Unassigned
Agent Lane: developer -> qa -> release
Branch: feat/ae-0036-export-preflight
Kanban Card: TBD
Created: 2026-06-09
Updated: 2026-06-09

## Goal

Reject carousel exports before screenshots when fonts, required images, copy geometry, overflow, or dimensions violate the presentation contract.

## Problem

Export currently waits a fixed duration and can accept broken images, fallback fonts, overlap, scrollable overflow, and odd-pixel crop artifacts.

## Scope

- Wait for `document.fonts.ready` and required font checks.
- Decode every required image and creator avatar when present.
- Measure lower-third geometry predicates for standard and HD.
- Count rendered text lines with `Range.getClientRects()`.
- Reject scrollable overflow.
- Produce per-slide geometry and image decode reports.
- Fix odd-pixel crop behavior.
- Add browser integration tests and fixtures.

## Non-Goals

- Renderer shell creation, which is AE-0035.
- Creator asset upload and staging, which is AE-0037.
- Artifact version activation, which is AE-0038.

## Acceptance Criteria

- [ ] WHEN slides 1 through 6 render THE Playwright preflight SHALL satisfy exact standard and HD geometry, line, font, overflow, and image predicates.
- [ ] WHEN lower-third copy exceeds client height or width THE EXPORT SHALL fail before screenshot.
- [ ] WHEN required background or avatar image decode fails THE EXPORT SHALL fail with slide, locale, and stable error code.
- [ ] WHEN required font families are unavailable THE EXPORT SHALL fail with `font_unavailable`.
- [ ] WHEN crop output differs from the target box beyond tolerated border artifacts THE EXPORT SHALL fail instead of silently accepting it.

## Gherkin Scenarios

```gherkin
Feature: Versioned carousel presentation contract

  Scenario: Lower-third copy overflows and export is rejected
    Given a presentation copy rectangle exceeds its client height by 2 pixels
    When standard export preflight runs
    Then layout overflow blocks the screenshot
    And no artifact version is activated

  Scenario: Background image cannot decode and export is rejected
    Given slide 4 references a required corrupt background
    When image decode preflight runs
    Then export fails with slide 4 and image_decode_failed
```

## Delta

### ADDED

- Playwright preflight evaluator.
- Font and image decode timeout handling.
- Geometry report objects.
- Browser fixtures for overflow, decode, fonts, and dimensions.

### MODIFIED

- Playwright export service.
- Cropping logic.
- Artifact health inputs.

### REMOVED

- Fixed-delay-only export readiness.
- Silent acceptance of undersized or mismatched output images.

## Affected Areas

- Backend: yes
- Frontend: no
- Database: no
- API: no
- Tests: yes
- Docs: no
- Prompts/LLM: no
- Observability: yes
- Deployment: no

## Dependencies

- Blocks: AE-0038, AE-0039
- Blocked by: AE-0035
- Related: AE-0033

## Implementation Plan

1. Add preflight report types and evaluator.
2. Wait for fonts and images with configured timeouts.
3. Measure geometry and line counts.
4. Integrate failures into export result.
5. Fix crop target calculation.
6. Add Playwright integration tests.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-09

Ticket created from AE-0028 architecture plan.

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

See [AE-0028.qa.md](../reports/AE-0028.qa.md) — AE-0036: **5/5 AC MET**, Review recommended.

## Decision Log

- Geometry predicates are machine gates; contact sheets are supporting evidence.

## Blockers

Blocked by AE-0035.

## Final Summary

Pending.
