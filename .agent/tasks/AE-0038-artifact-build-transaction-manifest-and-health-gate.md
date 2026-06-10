# AE-0038 — Artifact Build Transaction, Manifest, and Health Gate

Status: Review
Tier: T2
Priority: Critical
Type: Feature
Area: Backend/Publishing
Owner: Unassigned
Agent Lane: developer -> qa -> release
Branch: feat/ae-0038-artifact-builds
Kanban Card: TBD
Created: 2026-06-09
Updated: 2026-06-09

## Goal

Activate carousel artifacts through deterministic build records, immutable version directories, manifest validation, artifact health gates, and legacy read fallback.

## Problem

Current output paths are mutable and routes can serve incomplete or stale files. Export failures, concurrent refinements, stale cache keys, and DB/filesystem race conditions can leave publishable artifacts ambiguous.

## Scope

- Add `carousel_artifact_builds`.
- Implement staging, manifest writing, hash validation, immutable rename, compare-and-swap activation, recovery, retention, cleanup, and rollback.
- Add deterministic `artifact_version`.
- Resolve preview, publish, download, PDF, and media routes by database artifact version with legacy fallback.
- Extend artifact health with policy, validation, geometry, decode, avatar, manifest, hashes, counts, dimensions, and PDF checks.
- Reuse AE-0020 `generation_key` and AE-0023 normalized `output_dir`.

## Non-Goals

- Replacing image provider idempotency.
- Moving legacy files automatically.
- Implementing geometry preflight or creator asset upload, owned by AE-0036 and AE-0037.

## Acceptance Criteria

- [ ] WHEN artifact input is unchanged THE SYSTEM SHALL reuse the same valid artifact build without duplicate provider or rendering work.
- [ ] WHEN concurrent mutation or activation loses a compare-and-swap THE SYSTEM SHALL return a conflict and leave the active artifact unchanged.
- [ ] WHEN export, decode, font loading, PDF generation, or activation fails THE prior active artifact SHALL remain readable and no staging file SHALL be served.
- [ ] WHEN export succeeds THE SYSTEM SHALL activate one immutable `sha256-<64 hex>` version whose manifest hashes, counts, dimensions, policy, images, avatar, geometry, and PDFs all validate.
- [ ] WHEN `current.json` is missing or stale THE media routes SHALL resolve the database artifact version and the reconciler SHALL repair the index.
- [ ] WHEN a legacy project has null `artifact_version` THE dual-read routes SHALL continue serving its existing root layout without forced regeneration.

## Gherkin Scenarios

```gherkin
Feature: Versioned carousel presentation contract

  Scenario: Concurrent refinement loses optimistic lock and cannot promote
    Given two refinements start from the same lock version
    When the first candidate activates successfully
    Then the second compare-and-swap returns a conflict
    And the first artifact remains active

  Scenario: Export fails before promotion and prior artifact remains active
    Given a project has an active artifact
    And a new HD export times out in staging
    When the build is marked failed
    Then the prior artifact version remains in the database
    And media routes continue serving it
```

## Delta

### ADDED

- Artifact build records and statuses.
- Versioned output layout and manifest.
- Atomic promotion and activation logic.
- Reconciler, retention, cleanup, and rollback.
- Extended artifact health.

### MODIFIED

- Export orchestration.
- Media, preview, publish, download, and PDF routes.
- Cache behavior and artifact health responses.

### REMOVED

- Serving from `.staging` or unreferenced versions.
- Mutable output directory as serving authority for new projects.

## Affected Areas

- Backend: yes
- Frontend: yes
- Database: yes
- API: yes
- Tests: yes
- Docs: no
- Prompts/LLM: no
- Observability: yes
- Deployment: yes

## Dependencies

- Blocks: AE-0039
- Blocked by: AE-0033, AE-0036, AE-0037, AE-0020, AE-0021, AE-0022, AE-0023
- Related: AE-0028

## Implementation Plan

1. Add artifact build model, repository methods, and migration.
2. Compute deterministic artifact versions from canonical inputs.
3. Write staging outputs and manifest.
4. Validate files, hashes, geometry, images, avatar, PDFs, and policy.
5. Promote via atomic rename and compare-and-swap activation.
6. Update routes to resolve by active artifact version with legacy fallback.
7. Add recovery, cleanup, retention, rollback, and health tests.

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

- Database artifact version is serving authority; `current.json` is an operational index.

## Blockers

Blocked by AE-0033, AE-0036, AE-0037, AE-0020, AE-0021, AE-0022, and AE-0023.

## Final Summary

Pending.
