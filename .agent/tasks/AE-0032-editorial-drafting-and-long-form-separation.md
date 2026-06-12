# AE-0032 — Editorial Drafting and Long-Form Separation

Status: Review
Tier: T2
Priority: High
Type: Feature
Area: Backend/LLM
Owner: Unassigned
Agent Lane: developer -> qa -> release
Branch: feat/ae-0032-editorial-drafting
Kanban Card: TBD
Created: 2026-06-09
Updated: 2026-06-09

## Goal

Generate typed PT and EN presentation copy plus separate long-form notes for blog composition.

## Problem

The current workflow treats `draft_text` as both slide presentation copy and blog source material. Tightening slide copy without separating long-form notes would make generated blog content shallow.

## Scope

- Generate `CarouselDraftPackage` output from active editorial content drafting.
- Produce PT and EN presentation unions plus `long_form_notes`.
- Ensure PT and EN share slide type, content kind, selected structure, item counts, and Lucide `icon_name` shape.
- Refactor blog generation to use research, outline, and `long_form_notes`.
- Persist prompt, policy, instruction, model, source IDs, and confidence metadata.

## Non-Goals

- Defining the schema and migration, which is AE-0031.
- Blocking invalid persistence after repair, which is AE-0033.
- Frontend content review UI, which is AE-0034.

## Acceptance Criteria

- [ ] WHEN content drafting completes THE SYSTEM SHALL return seven PT and EN presentation unions plus `long_form_notes`.
- [ ] WHEN content slides include structured visual markers THE SYSTEM SHALL request and preserve allowlisted Lucide `icon_name` values.
- [ ] WHEN blog generation runs THE SYSTEM SHALL compose from research, outline, and `long_form_notes`, not constrained slide bodies.
- [ ] WHEN draft metadata is persisted THE SYSTEM SHALL include prompt version, policy version, instruction checksum, model ID, source IDs, and confidence score.
- [ ] WHEN translation output cannot be parsed THE SYSTEM SHALL surface a stable failure instead of returning an empty translation set.

## Gherkin Scenarios

```gherkin
Feature: Versioned carousel presentation contract

  Scenario: Valid bilingual carousel reaches content review
    Given hero_lower_third_v1 and carousel/v3 are active
    When seven structurally matching PT and EN slides are generated
    Then long_form_notes are available for blog generation
    And presentation bodies remain concise
```

## Delta

### ADDED

- Typed draft package generation path.
- Long-form notes persistence and blog composition input.
- Metadata persistence for prompt and instruction context.

### MODIFIED

- Content drafting agent output parsing.
- Editorial distribution pack persistence.
- Blog generation service.

### REMOVED

- Blog composition from concatenated constrained slide bodies.

## Affected Areas

- Backend: yes
- Frontend: no
- Database: yes
- API: no
- Tests: yes
- Docs: no
- Prompts/LLM: yes
- Observability: yes
- Deployment: no

## Dependencies

- Blocks: AE-0033, AE-0034, AE-0039
- Blocked by: AE-0031
- Related: AE-0030

## Implementation Plan

1. Update content drafting prompt invocation for typed package output.
2. Parse and persist PT/EN presentation copy and `long_form_notes`.
3. Preserve Lucide `icon_name` values through generation.
4. Refactor blog composition input.
5. Add tests for typed output, metadata, and blog separation.

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
cd backend && uv run pytest tests/unit/application/test_blog_composition.py tests/unit/application/test_editorial_distribution_pack.py -q
# 9 passed
```

## QA Report

Pending.

## Decision Log

- Slide copy and blog source material are separate outputs.

## Blockers

Blocked by AE-0031.

## Final Summary

Pending.
