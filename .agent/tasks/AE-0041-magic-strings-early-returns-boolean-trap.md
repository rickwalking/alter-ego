# AE-0041 — Magic Strings, Early Returns, Boolean Trap

Status: Dev Complete
Tier: T2
Priority: High
Type: Task
Area: Backend
Owner: Unassigned
Agent Lane: developer → qa
Branch: feat/ae-0041-magic-strings-early-returns
Kanban Card: AE-0041
Created: 2026-06-10
Updated: 2026-06-10

## Goal

Eliminate all magic strings, convert nested if chains to early returns with guard clauses, and replace boolean positional parameters with typed enums across the backend.

## Problem

PR #11 review flagged 7 instances of magic strings, 6 instances of deeply nested if statements, and 1 boolean trap (`dry_run: bool` as positional arg). These violate CLAUDE.md rules: "No magic strings" and "Early returns preferred — avoid nested if statements."

## Scope

### Magic Strings → Constants
- `repair_workflow_malformed_drafts.py:69` — `"intro"` → `SLIDE_TYPE_INTRO`
- `repair_workflow_malformed_drafts.py` — `"summary"`, `"content"`, `"closing"`, `"cta"` → existing constants
- `creator_asset_validation.py:94` — JPEG/PNG/WEBP magic bytes → new constants
- `carousel_presentation_adapters.py` — `"summary_points"`, `"actions"`, `"stats"`, `"features"`, `"insight"`, `"icon"` → existing or new constants
- `editorial_workflow_routes_response.py` — `"project_id"`, `"phase"`, etc. → `STATE_FIELD_*` constants
- `image_generation_records.py` — `"failed"`, `"recovered"`, `"reused"`, `"succeeded"` → existing constants

### Early Returns / If Simplification
- `recover_carousel_image_generations.py:126` — extract `_process_slide()` with guard clauses
- `repair_workflow_malformed_drafts.py:155` — extract `_polish_slide()`, guard for index != 1
- `image_generation_records.py:102` — inline ternary for `error_json`
- `regenerate_carousel_presentation.py:94` — dict dispatch for `_print_audit`
- `artifact_path_resolver.py` — `inner if statements` → early returns

### Boolean → Enum
- `recover_carousel_image_generations.py:108` — `dry_run: bool` → `RunMode` enum

## Non-Goals

- Changing function signatures beyond the boolean→enum replacement
- Refactoring the dispatch logic itself (handled in AE-0045)
- Touching frontend code

## Modularization Alignment (2026-06-12)

Wave A — architecture-neutral debt; execute first (plan rule: cleanup
before structure change). The touched files are future
`carousel_presentation` internals (Phase 5). Rules from the plan:

- Keep extracted constants **context-local** to the carousel files; do
  not create new global constants/helper modules that Phase 5 would
  immediately relocate (plan "Avoid" list).
- This ticket unblocks AE-0044/0045/0046 and must merge before any
  Phase 4-5 file movement (plan sequencing rule).
- No cross-layer imports may be added; AE-0078 baselines current
  violations and new ones will be visible.

## Acceptance Criteria

- [ ] All magic strings in scope replaced with named constants from `domain.constants.*` or new constants files
- [ ] `RunMode` enum created with `DRY_RUN`/`LIVE` members; `recover_project` signature updated
- [ ] Ruff `FBT001`/`FBT002` no longer suppressed for modified files
- [ ] All if chains >2 depth refactored with guard clauses + early returns
- [ ] `ruff check src/rag_backend/ —select S,ERA,FBT` passes on modified files
- [ ] All existing tests pass without modification

## Gherkin Scenarios

```gherkin
Feature: Magic Strings Eliminated

  Scenario: repair_workflow_malformed_drafts uses constants
    Given the file repair_workflow_malformed_drafts.py
    When searching for string literal "intro" outside constant definitions
    Then no matches should be found

Feature: Boolean Trap Eliminated

  Scenario: recover_project uses RunMode enum
    Given the function recover_project
    When inspecting its signature
    Then it must not contain "dry_run" as a boolean parameter

Feature: Early Returns

  Scenario: recover_carousel_image_generations has guard clauses
    Given the loop body in recover_project
    When inspecting control flow
    Then no nested if statement exceeds depth 2
```

## Delta

### ADDED

- `domain/constants/creator_asset.py` — magic byte constants
- `domain/constants/workflow_state_fields.py` — `STATE_FIELD_*` constants
- `domain/enums/run_mode.py` — `RunMode` enum
- Helper functions: `_process_slide()`, `_polish_slide()`, `_AUDIT_FIELDS` dispatch dict

### MODIFIED

- `scripts/recover_carousel_image_generations.py`
- `scripts/repair_workflow_malformed_drafts.py`
- `scripts/regenerate_carousel_presentation.py`
- `services/carousel/creator_asset_validation.py`
- `services/carousel/image_generation_records.py`
- `services/carousel/artifact_path_resolver.py`
- `domain/models/carousel_presentation_adapters.py`
- `api/routes/carousels/editorial_workflow_routes_response.py`

### REMOVED

- `dry_run: bool` parameter from `recover_project`

## Affected Areas

- Backend: All files listed in scope
- Frontend: None
- Database: None
- API: None
- Tests: Update assertions for new function signatures if any
- Docs: None
- Prompts/LLM: None
- Observability: None
- Deployment: None

## Dependencies

- Blocks: AE-0044 (builder uses `STATE_FIELD_*` constants)
- Blocked by: None
- Related: None

## Implementation Plan

1. Create `domain/constants/creator_asset.py` (magic bytes) and `domain/constants/workflow_state_fields.py`
2. Create `domain/enums/run_mode.py`
3. Replace magic strings in each file, verify with `ruff check`
4. Add guard clauses to each if-chain, extract helper functions where depth > 2
5. Replace `dry_run: bool` with `RunMode` enum in recovery script
6. Run full test suite: `cd backend && uv run pytest`
7. Run lint: `cd backend && uv run ruff check src/ --select S,ERA,FBT`

## QA Checklist

- [ ] Security reviewed — no auth/permission changes
- [ ] Code quality reviewed — ruff passes without blanket ignore
- [ ] Acceptance criteria validated
- [ ] Edge cases tested — empty strings, None values, unknown enums
- [ ] Orphan/unfinished code checked — no dead constants or duplicate constants

## Progress Log

### 2026-06-10

Ticket created.

## Files Touched

- domain/constants/creator_asset.py, workflow_state_fields.py (new)
- creator_asset_validation.py, editorial_workflow_routes_response.py
- scripts/regenerate_carousel_presentation.py, repair_workflow_malformed_drafts.py

## Test Evidence

```
ruff S,ERA,FBT: All checks passed
mypy strict: Success, 0 issues (389 files)
pytest: 1547 passed, 2 skipped
```

## QA Report

Pending.

## Decision Log

Pending.

## Blockers

None.

## Final Summary

Pending.
