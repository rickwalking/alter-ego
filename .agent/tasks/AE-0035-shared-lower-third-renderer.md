# AE-0035 — Shared Lower-Third Renderer

Status: Ready to Merge
Tier: T2
Priority: Critical
Type: Feature
Area: Backend/Renderer
Owner: Unassigned
Agent Lane: developer -> qa -> release
Branch: feat/ae-0035-lower-third-renderer
Kanban Card: TBD
Created: 2026-06-09
Updated: 2026-06-09

## Goal

Unify slides 1 through 6 under the lower-third presentation shell and render structured icons through controlled Lucide SVG output.

## Problem

Current strategies render unbounded content into inconsistent regions, allow scrollable overflow, and render structured `icon` values as raw text. This allows emoji and arbitrary icon strings into visible slide markup.

## Scope

- Add shared semantic markup for `.slide-artwork`, `.slide-overlay`, `.slide-presentation`, and `.slide-presentation-copy`.
- Update intro, hero, feature, stat, insight, numbered-list, and closing strategies.
- Keep CTA on a separate creator-card shell.
- Add renderer icon registry mapping allowlisted Lucide `icon_name` values to controlled inline SVG.
- Replace competing export CSS with shared CSS custom properties.
- Remove scrollable overflow from static presentation regions.
- Add HTML snapshot tests for all slide types and locales.

## Non-Goals

- Browser geometry measurement, which is AE-0036.
- Creator upload and staging, which is AE-0037.
- Artifact transactions, which are AE-0038.

## Acceptance Criteria

- [ ] WHEN slides 1 through 6 render THE MARKUP SHALL use the shared lower-third shell.
- [ ] WHEN structured `icon_name` values render THE SYSTEM SHALL output controlled Lucide inline SVG and SHALL NOT emit emoji characters.
- [ ] WHEN an unsupported icon name reaches render THE SYSTEM SHALL fail validation before render instead of rendering raw text.
- [ ] WHEN static slide regions render THE CSS SHALL NOT use scrollable overflow as a fitting strategy.
- [ ] WHEN standard and HD exports apply scale THE TEMPLATE SHALL use shared CSS variables instead of competing `!important` component overrides.

## Gherkin Scenarios

```gherkin
Feature: Versioned carousel presentation contract

  Scenario: Valid lower-third slide markup
    Given a hero_lower_third_v1 content slide
    When the renderer builds HTML
    Then the slide contains the shared lower-third shell
    And structured icons are rendered as controlled Lucide SVG

  Scenario: Lower-third copy overflows and export is rejected
    Given static presentation regions contain no scrollable overflow
    When copy exceeds the available area
    Then later geometry preflight can reject the screenshot
```

## Delta

### ADDED

- Lower-third shell markup helpers.
- Lucide SVG icon registry.
- Renderer snapshot tests.

### MODIFIED

- Intro, hero, feature, stat, insight, numbered-list, and closing strategies.
- Carousel template CSS.
- Export CSS variable contract.

### REMOVED

- Raw emoji/text icon rendering for new structured items.
- Scrollable overflow in static presentation regions.

## Affected Areas

- Backend: yes
- Frontend: no
- Database: no
- API: no
- Tests: yes
- Docs: no
- Prompts/LLM: no
- Observability: no
- Deployment: no

## Dependencies

- Blocks: AE-0036, AE-0038, AE-0039
- Blocked by: AE-0030
- Related: AE-0031, AE-0033

## Implementation Plan

1. Add reusable lower-third render helpers.
2. Add Lucide icon registry and renderer API.
3. Update slide strategies.
4. Replace export-scale overrides with CSS variables.
5. Add HTML and CSS snapshot tests.

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

```bash
cd backend && uv run pytest tests/unit/application/strategies/ -q
# 102 passed
```

## QA Report

See [AE-0028.qa.md](../reports/AE-0028.qa.md) — AE-0035: **5/5 AC MET**, Review recommended.

## Decision Log

- Renderer never trusts raw LLM icon text.

## Blockers

Blocked by AE-0030.

## Final Summary

Pending.
