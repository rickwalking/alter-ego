# AE-0050 — Rollback, Migration, and Observability Safeguards

Status: Intake
Tier: T2
Priority: Medium
Type: Task
Area: Cross-cutting
Owner: Unassigned
Agent Lane: developer → qa
Branch: feat/ae-0050-safeguards
Kanban Card: AE-0050
Created: 2026-06-10
Updated: 2026-06-10

## Goal

Install deprecation wrappers for all changed function signatures across the refactoring. Verify Langfuse trace metadata is preserved after refactoring. Document rollback procedures. Add `high_risk_areas` tags to ticket metadata.

## Problem

The refactoring in AE-0041 through AE-0048 changes internal function signatures and module structure. Without safeguards:
1. In-flight editorial workflows (PR #11 still open) could break if functions are renamed or have new signatures
2. Langfuse traces could lose `project_id`, `phase`, `agent_name` metadata if refactored code changes how callbacks are wired
3. Rollback of individual components is not documented

## Scope

### Deprecation Wrappers
For every public function whose signature changes, add a wrapper:

```python
import warnings

def old_name(*args: object, **kwargs: object) -> object:
    warnings.warn(
        "old_name is deprecated, use new_name",
        DeprecationWarning,
        stacklevel=2,
    )
    return new_name(*args, **kwargs)
```

Functions requiring wrappers (inventory):
- `build_workflow_state_response` → refactored to use `_FIELD_MAPPING` (AE-0044)
- `resolve_presentation_review_from_state` → refactored to Chain-of-Responsibility (AE-0045)
- `build_presentation_review_updates`/`_async` → refactored to `_build_presentation_review_common` (AE-0045)
- `resolve_artifact_serving_paths` → renamed to `resolve_and_reconcile_serving_paths` (AE-0043)
- `recover_project` → `dry_run: bool` → `RunMode` enum (AE-0041)
- `validate_localized_slides` → may be restructured internally

### Langfuse Trace Verification
- Audit all refactored functions for `get_langfuse_handler()` calls
- Verify that refactored code still propagates `project_id`, `phase`, `agent_name`, `user_id`, `content_type` metadata
- Add integration test that spies on Langfuse calls during editorial workflow operations
- Document required trace metadata per function in module docstrings

### Rollback Documentation
- For each AE-0041 through AE-0049 ticket, document exact `git revert` command
- Document order of reverts (reverse of execution order)
- Update `.agent/BOARD.md` rollback column if it exists, or add to ticket Decision Logs

### high_risk_areas Tagging
Per `CLAUDE.md` requirements, tag these as high risk:
- AE-0044 (Builder): MEDIUM — API response builder change
- AE-0045 (Strategy): MEDIUM — presentation logic change
- AE-0048 (Ignores): HIGH — CI breakage risk

## Non-Goals

- Changing the refactoring scope or execution order
- Adding new Langfuse tracing beyond what already exists
- Creating an automated rollback script

## Modularization Alignment (2026-06-12)

Runs alongside Wave B — its deprecation-wrapper inventory covers
AE-0043/0044/0045 signature changes. Alignment:

- Wrapper windows must close **before Phase 4 starts** so compatibility
  facades never wrap deprecated functions (one indirection, not two).
- Type the wrappers properly (mirror the new signature); the `*args:
  object` example in Scope violates the no-`object` rule — implement
  with explicit parameters.
- The rollback-procedure docs should adopt the plan's side-effect and
  compatibility ledger format (see "Rollout and Rollback"), so Phase 1+
  slices reuse the same template.
- Langfuse metadata verification (project_id, phase, agent_name,
  user_id, content_type) doubles as the plan's operational-equivalence
  groundwork; record the verified list in the ticket.
- `high_risk_areas` tags feed the architect-skill skeptical-review
  trigger — include the carousel workflow, event emission, and artifact
  paths.

## Acceptance Criteria

- [ ] All changed public functions have `@deprecated` wrappers with `DeprecationWarning`
- [ ] All deprecation wrappers document the new function name in the warning message
- [ ] Langfuse trace metadata audit completed for all refactored functions
- [ ] Integration test verifies Langfuse traces during editorial workflow operations
- [ ] Rollback `git revert` commands documented for each ticket
- [ ] `high_risk_areas` tags added to AE-0044, AE-0045, AE-0048 ticket metadata
- [ ] All existing tests pass — deprecation wrappers ensure backward compatibility

## Gherkin Scenarios

```gherkin
Feature: Deprecation Wrappers

  Scenario: old function name still works
    Given code calls the old function name
    When it executes
    Then a DeprecationWarning is issued
    And the result is identical to the new function

Feature: Langfuse Trace Preservation

  Scenario: refactored function preserves traces
    Given a refactored function with Langfuse callback
    When it executes with project_id, phase, agent_name
    Then the trace includes all metadata fields
```

## Delta

### MODIFIED

- All files touched by AE-0041 through AE-0047 (deprecation wrappers)
- `.agent/tasks/AE-0044.md`, `AE-0045.md`, `AE-0048.md` — high_risk_areas tags

### ADDED

- Integration test for Langfuse trace metadata
- Rollback documentation in Decision Logs

## Affected Areas

- Backend: Deprecation wrappers across multiple modules
- Tests: New integration test for Langfuse traces
- Docs: Rollback procedures per ticket

## Dependencies

- Blocks: None
- Blocked by: AE-0044, AE-0045, AE-0048 (runs after all refactoring is complete)
- Related: All AE-0041 through AE-0049

## Implementation Plan

1. Audit all refactored functions for Langfuse handler propagation
2. Add deprecation wrappers for each changed public function
3. Write integration test that verifies Langfuse metadata in traces
4. Document rollback commands in each ticket's Decision Log
5. Add `high_risk_areas` tags to relevant tickets
6. Run full test suite to verify backward compatibility
7. Update CLAUDE.md if any new patterns emerge

## QA Checklist

- [ ] Security reviewed — no auth changes
- [ ] Code quality reviewed — no type: ignore added
- [ ] Acceptance criteria validated
- [ ] Edge cases tested — old function called with new-style args, deprecation warning not raised in test mode
- [ ] Orphan/unfinished code checked — no dead wrappers

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

Blocked by: AE-0044, AE-0045, AE-0048

## Final Summary

Pending.
