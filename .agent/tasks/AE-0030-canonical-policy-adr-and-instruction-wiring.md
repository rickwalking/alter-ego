# AE-0030 — Canonical Policy, ADR Amendment, and Instruction Wiring

Status: Review
Tier: T2
Priority: Critical
Type: Feature
Area: Backend/Prompts
Owner: Unassigned
Agent Lane: developer -> qa -> release
Branch: feat/ae-0030-carousel-policy
Kanban Card: TBD
Created: 2026-06-09
Updated: 2026-06-09

## Goal

Create the canonical `hero_lower_third_v1` presentation policy and wire its generated instruction context into the active editorial agents.

## Problem

The active carousel workflow does not receive the documented presentation rules. Editing skill markdown alone cannot enforce seven slides, lower-third copy, dash and emoji policy, Lucide icon names, or geometry requirements.

## Scope

- Add `skills/runtime/carousel-pipeline/contracts/hero_lower_third_v1.yaml`.
- Add typed policy loader objects and checksum calculation.
- Add `carousel/v3` prompt files and generated policy context.
- Add `CarouselInstructionContextLoader`.
- Update runtime shared and phase skill docs, including replacing emoji icon guidance with Lucide `icon_name` allowlist guidance.
- Amend ADR-007 implementation notes.
- Add cross-layer drift tests for YAML, typed policy, prompt context, packaged files, shared docs, Lucide icon allowlist, and ADR paths.

## Non-Goals

- Persisting new slide union payloads.
- Implementing geometry preflight.
- Moving delivery skills, which is AE-0029.

## Acceptance Criteria

- [ ] WHEN canonical YAML, generated prompt context, typed policy, packaged runtime files, shared rule references, or Lucide icon allowlists diverge THE CI drift test SHALL fail with mismatched identifiers.
- [ ] WHEN `hero_lower_third_v1` loads THE SYSTEM SHALL expose slide count, slide types, copy budgets, visible-text rules, geometry ratios, font checks, and Lucide icon allowlist from the typed policy.
- [ ] WHEN `OutlineAgent` or `ContentDraftAgent` runs THE SYSTEM SHALL pass bounded instruction context containing policy, schema, locale, phase, persona, and revision notes.
- [ ] WHEN runtime skill docs mention structured icons THE DOCS SHALL use Lucide `icon_name` values and SHALL NOT request emoji icons.
- [ ] WHEN instruction context is logged THE SYSTEM SHALL persist prompt version, policy version, instruction checksum, model ID, phase, and slide number.

## Gherkin Scenarios

```gherkin
Feature: Versioned carousel presentation contract

  Scenario: Valid bilingual carousel reaches content review
    Given hero_lower_third_v1 and carousel/v3 are active
    When the content agent receives generated policy instructions
    Then it requests seven structurally typed slides
    And structured icons are requested as Lucide icon_name values

  Scenario: Runtime documentation drifts from canonical policy
    Given shared runtime documentation omits a required rule identifier
    When contract-alignment tests run
    Then the test fails with the missing rule identifier
```

## Delta

### ADDED

- Canonical `hero_lower_third_v1.yaml`.
- `presentation_policy.py`.
- `carousel/v3` prompts.
- `CarouselInstructionContextLoader`.
- Contract-alignment tests.

### MODIFIED

- ADR-007.
- Runtime carousel shared and phase skill docs.
- Active editorial agent construction.
- Prompt registry usage for carousel content.

### REMOVED

- Active dependency on `domain/constants/ai_agents.py` for carousel editorial prompts.
- Emoji icon instructions from runtime carousel skills.

## Affected Areas

- Backend: yes
- Frontend: no
- Database: no
- API: no
- Tests: yes
- Docs: yes
- Prompts/LLM: yes
- Observability: yes
- Deployment: yes

## Dependencies

- Blocks: AE-0031, AE-0032, AE-0033, AE-0034, AE-0035, AE-0036, AE-0037, AE-0038, AE-0039
- Blocked by: AE-0029
- Related: AE-0028

## Implementation Plan

1. Add canonical policy YAML and typed policy loader.
2. Generate prompt-safe policy context from typed policy.
3. Create `carousel/v3` prompt files.
4. Wire instruction loader into active editorial agents.
5. Replace runtime skill emoji icon guidance with Lucide `icon_name` allowlist guidance.
6. Add drift tests and ADR-007 amendment.

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

Pending.

## Decision Log

- Policy YAML is canonical; Python and prompts reflect it.
- Lucide semantic icon names are part of the visible-slide contract.

## Blockers

Blocked by AE-0029.

## Final Summary

Pending.
