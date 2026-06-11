# AE-0043 — Segregate Overloaded Functions

Status: Intake
Tier: T2
Priority: Medium
Type: Task
Area: Backend
Owner: Unassigned
Agent Lane: developer → qa
Branch: feat/ae-0043-segregate-overloaded-functions
Kanban Card: AE-0043
Created: 2026-06-10
Updated: 2026-06-10

## Goal

Split functions that handle multiple responsibilities or code paths (update vs create, legacy vs versioned) into separate focused functions. Deduplicate repeated patterns across artifact path resolvers.

## Problem

PR #11 review flagged:
- `editorial_distribution_persist.py`: `apply_slide_drafts_to_database` has two divergent code paths (update vs create) in one function
- `artifact_path_resolver.py`: 6 functions repeat `resolve_artifact_serving_paths(project)` as first line; also `resolve_artifact_serving_paths` has side effect (`reconcile_current_index`)
- `artifact_manifest.py`: `to_payload()` repeats the same conversion pattern 5 times

## Scope

### `apply_slide_drafts_to_database` split
- Extract `_update_existing_slides(context, existing)`
- Extract `_create_new_slides(context)`
- Main function becomes: `if existing: await _update... else: await _create...`

### `artifact_path_resolver.py` dedup
- Extract `_resolve_base(project) -> ArtifactPaths | None` dataclass helper
- 6 other functions use `_resolve_base` instead of calling `resolve_artifact_serving_paths`
- Rename `resolve_artifact_serving_paths` to `resolve_and_reconcile_serving_paths` (documents side effect)

### `artifact_manifest.py` dedup
- Create generic `_slide_records(entries) -> list[ArtifactSlideFileRecord]` helper
- Call it 5 times instead of repeating the same list comprehension

## Non-Goals

- Changing the public API contracts (return types stay identical)
- Architectural pattern changes (Strategy/Builder handled in AE-0044, AE-0045)
- Performance optimization beyond deduplication

## Acceptance Criteria

- [ ] `apply_slide_drafts_to_database` refactored into 3 focused functions
- [ ] `_resolve_base(Path) -> ArtifactPaths | None` extracted and reused by 6 functions
- [ ] `resolve_artifact_serving_paths` renamed to document its side effect
- [ ] `_slide_records()` helper created and used 5 times in `artifact_manifest.py`
- [ ] All existing tests pass without modification
- [ ] Coverage on modified files stays >= current level

## Gherkin Scenarios

```gherkin
Feature: Function Segregation

  Scenario: apply_slide_drafts_to_database with existing slides
    Given existing slides in the database
    When apply_slide_drafts_to_database is called
    Then _update_existing_slides is invoked
    And _create_new_slides is not invoked

  Scenario: apply_slide_drafts_to_database without existing slides
    Given no existing slides in the database
    When apply_slide_drafts_to_database is called
    Then _create_new_slides is invoked
    And _update_existing_slides is not invoked

Feature: Path Resolver Dedup

  Scenario: resolve_language_dir uses _resolve_base
    Given resolve_language_dir is called
    When inspecting its implementation
    Then it calls _resolve_base and does not call resolve_artifact_serving_paths directly
```

## Delta

### MODIFIED

- `services/carousel/editorial_distribution_persist.py`
- `services/carousel/artifact_path_resolver.py`
- `services/carousel/artifact_manifest.py`

### ADDED

- `ArtifactPaths` dataclass in `artifact_path_resolver.py`
- `_slide_records()` helper in `artifact_manifest.py`

### RENAMED

- `resolve_artifact_serving_paths` → `resolve_and_reconcile_serving_paths`

## Affected Areas

- Backend: 3 service files
- Tests: Integration tests for editorial_distribution_persist; unit tests for artifact_path_resolver
- Docs: None
- Observability: None

## Dependencies

- Blocks: None
- Blocked by: None
- Related: AE-0044, AE-0045

## Implementation Plan

1. Extract `ArtifactPaths` dataclass + `_resolve_base` in `artifact_path_resolver.py`
2. Refactor 6 path resolver functions to use `_resolve_base`
3. Rename `resolve_artifact_serving_paths`
4. Create `_slide_records()` in `artifact_manifest.py`
5. Split `apply_slide_drafts_to_database` into 3 functions
6. Run tests: `cd backend && uv run pytest`
7. Verify coverage: `cd backend && uv run pytest --cov=rag_backend`

## QA Checklist

- [ ] Code quality reviewed — no nested ifs >2 depth
- [ ] Acceptance criteria validated
- [ ] Edge cases tested — empty slides, missing output_dir
- [ ] Orphan/unfinished code checked — old function names still callable

## Progress Log

### 2026-06-10

Ticket created.

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Decision Log

Pending.

## Blockers

None.

## Final Summary

Pending.
