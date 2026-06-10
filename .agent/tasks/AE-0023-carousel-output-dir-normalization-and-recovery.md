# AE-0023 — Carousel Output Directory Normalization and Recovery Tooling

Status: Review
Tier: T2
Priority: High
Type: Bugfix
Area: Backend/DevOps
Owner: Unassigned
Agent Lane: architect -> developer -> qa -> release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-08
Updated: 2026-06-08

## Goal

Ensure carousel artifacts are written under the configured output root and provide safe recovery tooling for existing generated images.

## Problem

Some projects persist relative output paths such as `output/carousels/{id}` while working container artifacts live under `/app/output/carousels/{id}`. This makes media lookup, recovery, and validation ambiguous.

## Scope

- Inject configured `settings.carousel_output_dir` into carousel image generation.
- Persist resolved absolute output dirs.
- Remove independent `./output/carousels` defaults.
- Add recovery/backfill tooling for existing image files and generation records.
- Document current environment remediation steps, including admin password reset.

## Non-Goals

- Artifact health service implementation.
- Prompt package editing.
- Provider error extraction.

## Acceptance Criteria

- [ ] WHEN a new carousel enters image generation THE SYSTEM SHALL persist an absolute output_dir rooted at configured `carousel_output_dir`.
- [ ] WHEN image generation builds output paths THE SYSTEM SHALL use injected configuration, not a local `DEFAULT_OUTPUT_BASE`.
- [ ] WHEN existing relative output_dir rows are recovered THE TOOL SHALL normalize or report them without deleting files.
- [ ] WHEN valid existing image files are recovered THE TOOL SHALL create recovered generation records.
- [ ] WHEN an operational remediation is documented THE DOC SHALL include resetting `admin@alterego.app` to the expected password without exposing secrets.

## Gherkin Scenarios

```gherkin
Feature: Carousel output directory normalization

  Scenario: New image generation uses configured output root
    Given carousel_output_dir is "/app/output/carousels"
    When image generation starts for a project
    Then project.output_dir is "/app/output/carousels/{project_id}"

  Scenario: Recovery reports relative output directory
    Given a project output_dir is "output/carousels/project-id"
    When the recovery tool audits the project
    Then it reports the relative path
    And it does not delete any files
```

## Delta

### ADDED

- Output directory normalization tests.
- Recovery/backfill command or script.
- Recovery documentation.

### MODIFIED

- `backend/src/rag_backend/application/services/carousel/editorial_visual_pipeline.py`
- `backend/src/rag_backend/application/services/carousel/phase_artifact_runner.py`
- `backend/src/rag_backend/agents/carousel_editorial_orchestrator.py`
- Dependency injection/container wiring.

### REMOVED

- Independent `DEFAULT_OUTPUT_BASE = "./output/carousels"` usage in image generation.

## Affected Areas

- Backend: yes
- Frontend: no
- Database: yes
- API: no
- Tests: yes
- Docs: yes
- Prompts/LLM: no
- Observability: yes
- Deployment: yes

## Dependencies

- Blocks: AE-0024
- Blocked by: AE-0020
- Related: `.agent/reports/carousel-generation-recovery-plan.md`

## Implementation Plan

1. Add output root to typed orchestrator/runner dependencies.
2. Pass settings-derived output root through DI.
3. Build and persist absolute output dirs.
4. Add tests using temp output roots.
5. Add recovery/backfill command for existing image files.
6. Add docs for environment cleanup and credential reset.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-08

Ticket created from AE-0017 epic.

Developer implementation replaced the independent `DEFAULT_OUTPUT_BASE` image
generation fallback with `settings.carousel_output_dir` and persists the
resolved output path for new image generation. Remaining scope: inject the root
through orchestrator/runner dependencies, normalize existing relative rows,
add recovery/backfill tooling, and document operational remediation steps.

## Files Touched

backend/src/rag_backend/application/services/carousel/editorial_visual_pipeline.py

## Test Evidence

Covered by focused backend lint. Dedicated temp-root normalization tests remain.

## QA Report

See [.agent/reports/AE-0018-AE-0023.qa.md](../reports/AE-0018-AE-0023.qa.md)

**Status**: Review
**Overall Score**: 50% on AC (2/4 pass)

**Blocker Findings**:
- No recovery/backfill tool exists to normalize relative output_dir rows
- No recovery/backfill tool exists to create recovered generation records for existing disk files

**Warning Findings**: None for AE-0023 scope

## Decision Log

- Recovery tooling must be non-destructive by default.

## Blockers

- Recovery tool implementation is entirely missing (noted as remaining scope in dev summary).
- Output dir normalization for new projects is correctly implemented.

## Final Summary

New image generation correctly uses `settings.carousel_output_dir` and persists absolute paths. No `DEFAULT_OUTPUT_BASE` remains. However, both recovery/backfill tooling criteria fail — no standalone script exists to normalize existing relative rows or create recovered records.
