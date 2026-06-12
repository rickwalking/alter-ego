# AE-0042 — Null-Safety and Exception Suppression

Status: Intake
Tier: T2
Priority: High
Type: Task
Area: Backend
Owner: Unassigned
Agent Lane: developer → qa
Branch: feat/ae-0042-null-safety-exception-suppression
Kanban Card: AE-0042
Created: 2026-06-10
Updated: 2026-06-10

## Goal

Fix unsafe property access without null-checks in `artifact_manifest.py` (`manifest_from_payload`), eliminate silent exception suppression in `image_generation_records.py`, and add safe access patterns throughout affected modules.

## Problem

PR #11 review flagged:
- `manifest_from_payload`: access nested TypedDict properties without null-checking — "is it safe to access all these properties without checking?"
- `presentation_review_edits.py:69`: "assignment without checking for nullable values"
- `image_generation_records.py`: `reuse_recorded_generation` silently suppresses `AttributeError` and `NotImplementedError`

## Scope

### Safe Access in `manifest_from_payload`
- Convert `CarouselArtifactManifestPayload` from raw TypedDict to a Pydantic `BaseModel` with proper defaults and validators
- Replace unsafe `payload["key"]` access with typed `.key` access
- Add `field_validator` for critical numeric/string fields

### Null-Check in `presentation_review_edits.py`
- Add explicit `None` guard clauses before assignment in `_apply_edits_to_drafts`
- Extract helper `_safe_str(value: object, default: str = "") -> str`

### Exception Suppression in `image_generation_records.py`
- Replace `except (AttributeError, NotImplementedError):` with `except NotImplementedError:`
- Add `hasattr()` check before attribute access
- Log warnings at `logger.warning()` for suppressed errors
- Add explicit return type tests

## Non-Goals

- Changing the public API of `manifest_from_payload` (return type stays `CarouselArtifactManifest`)
- Adding new database migrations
- Touching frontend

## Acceptance Criteria

- [ ] `CarouselArtifactManifestPayload` converted to Pydantic `BaseModel` with typed fields and validators
- [ ] `manifest_from_payload` uses safe `.key` access (no bare `payload["key"]`)
- [ ] Exception suppression replaced with explicit `hasattr` + `logger.warning` in `reuse_recorded_generation`
- [ ] `_apply_edits_to_drafts`: all nullable assignments guarded with `if X is not None` or `_safe_str()`
- [ ] mypy strict passes on modified files
- [ ] All existing tests pass

## Gherkin Scenarios

```gherkin
Feature: Null-Safe Manifest Building

  Scenario: manifest_from_payload with missing optional field
    Given a payload missing the policy_version field
    When manifest_from_payload is called
    Then policy_version is None in the result

  Scenario: manifest_from_payload with invalid raw_image_hashes
    Given a payload with raw_image_hashes=None
    When manifest_from_payload is called
    Then raw_image_hashes is an empty list in the result

Feature: No Exception Suppression

  Scenario: repository without get_image_generation_by_key
    Given a repository that lacks get_image_generation_by_key
    When reuse_recorded_generation is called
    Then it returns None and logs a warning
```

## Delta

### MODIFIED

- `services/carousel/artifact_manifest.py`
- `services/carousel/presentation_review_edits.py`
- `services/carousel/image_generation_records.py`

### ADDED

- `_safe_str()` helper or in `services/carousel/presentation_review_edits.py`

## Affected Areas

- Backend: artifact_manifest, presentation_review_edits, image_generation_records
- Frontend: None
- Database: None
- API: None
- Tests: Add tests for null-safety and exception scenarios
- Docs: None
- Prompts/LLM: None
- Observability: Logger warnings added

## Dependencies

- Blocks: None
- Blocked by: None
- Related: AE-0041 (may use same constants file)

## Implementation Plan

1. Define `CarouselArtifactManifestPayload` as Pydantic BaseModel
2. Add `field_validator` for each critical field
3. Update `manifest_from_payload` to use `.key` access
4. Add `_safe_str()` helper to `presentation_review_edits.py`
5. Guard nullable assignments in `_apply_edits_to_drafts`
6. Replace `except (AttributeError, NotImplementedError)` in `image_generation_records.py`
7. Add unit tests for null-safety and exception scenarios
8. Run `mypy` and `ruff` on modified files

## QA Checklist

- [ ] Security reviewed — no auth changes
- [ ] Code quality reviewed — no new type: ignore
- [ ] Acceptance criteria validated
- [ ] Edge cases tested — None payloads, missing fields, empty lists
- [ ] Orphan/unfinished code checked

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
