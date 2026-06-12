# AE-0031 — Discriminated Bilingual Slide Schema and Migration

Status: Review
Tier: T2
Priority: Critical
Type: Feature
Area: Backend/Database
Owner: Unassigned
Agent Lane: developer -> qa -> release
Branch: feat/ae-0031-slide-schema
Kanban Card: TBD
Created: 2026-06-09
Updated: 2026-06-09

## Goal

Replace free-form persisted slide extras with a discriminated, bilingual slide presentation schema while preserving legacy reads.

## Problem

Current slide rows store headings, bodies, and arbitrary extras without a typed distinction between presentation copy and long-form material. PT and EN structures can drift, translation parse failures can become empty data, and emoji icon strings are accepted as raw presentation content.

## Scope

- Add Pydantic models for `CarouselDraftPackage`, `SlideDraft`, slide copy unions, structured items, and validation reports.
- Add `presentation_policy_version`, `presentation_policy_checksum`, `artifact_version`, `creator_website`, and `creator_asset_id` columns.
- Add creator asset and artifact build tables needed by downstream tickets.
- Replace new structured item `icon` writes with allowlisted Lucide `icon_name`.
- Add compatibility adapters for legacy `features`, `stats`, `insight`, `summary_points`, and `tldr_strip`.
- Add Alembic upgrade/downgrade and legacy-read tests.

## Non-Goals

- Generating the new typed draft package, which is AE-0032.
- Blocking validation and repair, which is AE-0033.
- Implementing renderer output for Lucide SVGs, which is AE-0035.

## Acceptance Criteria

- [ ] WHEN a seven-slide draft is generated THE SYSTEM SHALL represent PT and EN as matching discriminated unions with separate long-form notes.
- [ ] WHEN structured item icons are persisted for new `hero_lower_third_v1` projects THE SYSTEM SHALL persist `icon_name` using only allowlisted Lucide names.
- [ ] WHEN legacy rows contain `icon` or old structured extras THE SYSTEM SHALL read them through compatibility adapters without rewriting them.
- [ ] WHEN PT and EN structured shapes differ THE SYSTEM SHALL report `translation_shape_mismatch`.
- [ ] WHEN downgrade runs while projects use `hero_lower_third_v1` THE MIGRATION SHALL fail with an operator-facing message.

## Gherkin Scenarios

```gherkin
Feature: Versioned carousel presentation contract

  Scenario: PT and EN structured shapes differ and generation fails
    Given PT content uses features
    And EN content uses stats
    When structural parity is validated
    Then translation_shape_mismatch blocks persistence

  Scenario: Legacy carousel remains readable without forced regeneration
    Given a legacy slide has extras with icon fields
    When the repository loads the slide
    Then compatibility data is returned
    And the row is not rewritten
```

## Delta

### ADDED

- Slide union Pydantic models.
- Structured `icon_name` field validation.
- Alembic migration for policy, artifact, and creator asset foundation.
- Legacy read adapters and tests.

### MODIFIED

- Carousel project and slide serialization.
- Repository read/write paths.
- API schemas for project response fields.

### REMOVED

- New writes of raw structured item `icon` fields for `hero_lower_third_v1`.

## Affected Areas

- Backend: yes
- Frontend: no
- Database: yes
- API: yes
- Tests: yes
- Docs: no
- Prompts/LLM: no
- Observability: no
- Deployment: yes

## Dependencies

- Blocks: AE-0032, AE-0033, AE-0034, AE-0038, AE-0039
- Blocked by: AE-0030
- Related: AE-0020, AE-0023

## Implementation Plan

1. Add Pydantic models with `extra="forbid"`.
2. Add policy/artifact/creator database migration.
3. Update domain and database models.
4. Add compatibility adapters for legacy extras.
5. Enforce `icon_name` field shape for new union payloads.
6. Add unit and migration tests.

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

- Existing JSONB remains the rich slide storage location.
- `icon_name` is the new structured icon field.

## Blockers

Blocked by AE-0030.

## Final Summary

Pending.
