# AE-0017 — Carousel Generation Recovery and Artifact Integrity Epic

Status: Review
Tier: T3
Priority: Critical
Type: Epic
Area: Cross-cutting
Owner: Unassigned
Agent Lane: planner -> architect -> developer -> qa -> release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-08
Updated: 2026-06-08

## Goal

Make carousel generation reliable, observable, recoverable, and publish-safe from image prompt review through rendered slide export.

## Problem

The carousel pipeline can expose four raw image URLs when seven rendered slides are expected, can mark manually mutated placeholder outputs as publish-ready, and does not persist enough image-generation metadata to reuse successful images or explain OpenAI failures clearly.

## Scope

- Backend artifact health validation for raw images, rendered PT/EN slides, HD slides, and PDFs.
- Image-generation records with idempotency keys, response/error metadata, and recovery/backfill.
- Prompt package visibility and editing before OpenAI calls.
- OpenAI/provider error capture, workflow visibility, and structured logs.
- Removal of four-slide/raw-image fallback paths from API, preview, publish, and Instagram publish.
- Output directory normalization to configured carousel output root.
- Clean regeneration and visual QA evidence.

## Non-Goals

- Broad visual redesign; AE-0013 covers render polish.
- Changing CTA raw image rules unless separately approved.
- Copying raw images into `pt/` or `en/` as a substitute for rendered export.
- Replacing the accepted ADR-007 editorial workflow architecture with a new queue system.

## Acceptance Criteria

- [ ] WHEN a carousel has seven DB slides THE SYSTEM SHALL NOT expose only four preview or publish slides.
- [ ] WHEN rendered PT/EN slides, HD slides, or PDFs are incomplete THE SYSTEM SHALL block final approval or publish.
- [ ] WHEN an OpenAI image call fails THE SYSTEM SHALL preserve structured provider error details and show a recoverable workflow error.
- [ ] WHEN the same image prompt/theme/model already generated a valid image THE SYSTEM SHALL reuse it without another OpenAI call.
- [ ] WHEN image prompts are reviewed THE UI SHALL show editable prompt details, final provider prompt, theme, colors, model, and generation key.
- [ ] WHEN a clean carousel run completes THE SYSTEM SHALL pass `scripts/carousel_visual_qa.py` for PT and EN rendered slides.

## Gherkin Scenarios

```gherkin
Feature: Carousel generation recovery

  Scenario: Incomplete rendered exports block publish
    Given a carousel project is marked approved_for_publish
    And the project is missing PT HD rendered slides
    When the user publishes the carousel
    Then the API returns a conflict
    And the carousel remains unpublished

  Scenario: Existing successful image generation is reused
    Given a slide has a succeeded image generation record
    And the prompt, model, style, and theme are unchanged
    When the image phase retries
    Then the provider is not called for that slide
    And the existing image_path is reused
```

## Delta

### ADDED

- AE-0018 artifact health gate.
- AE-0019 image prompt package and review contract.
- AE-0020 image generation records and idempotency.
- AE-0021 provider error visibility and structured logs.
- AE-0022 rendered slide contract and four-slide fallback removal.
- AE-0023 output directory normalization and recovery tooling.
- AE-0024 clean regeneration QA.
- AE-0025 workflow resume interrupt checkpoint corruption fix.
- AE-0026 get_state() phase_status override fix.
- AE-0027 background resume stuck detection.

### MODIFIED

- Carousel generation workflow and publish path acceptance criteria.
- Existing AE-0011 and AE-0012 prompt-review surface expectations.

### REMOVED

- Four-slide fallback as an acceptable preview/publish state.

## Affected Areas

- Backend: yes
- Frontend: yes
- Database: yes
- API: yes
- Tests: yes
- Docs: yes
- Prompts/LLM: yes
- Observability: yes
- Deployment: yes

## Dependencies

- Blocks: AE-0018, AE-0019, AE-0020, AE-0021, AE-0022, AE-0023, AE-0024
- Blocked by: none
- Related: `.agent/reports/carousel-generation-recovery-plan.md`, AE-0010, AE-0011, AE-0012, AE-0013 visual polish plan

## Implementation Plan

1. Ship artifact health validation and publish gates.
2. Expose complete prompt packages and editable image prompt review.
3. Persist image generation attempts with idempotency and recovery metadata.
4. Add provider error handling, workflow visibility, and logs.
5. Remove raw/four-slide fallback behavior from backend and frontend.
6. Normalize output dirs and add recovery/backfill tooling.
7. Run clean regeneration and visual QA.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-08

Epic created from carousel generation recovery architecture plan.

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Decision Log

- Use the existing ADR-007 editorial workflow direction.
- Treat raw AI images and rendered carousel slides as separate artifact contracts.
- Reject copying raw images into language export directories as a valid fix.

## Blockers

None.

## Final Summary

Pending.
