# AE-0050 — Rollback, Migration, and Observability Safeguards

Status: Dev Complete
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

### 2026-06-12 (developer)

Inventoried existing deprecation wrappers (most already landed in waves 3-4),
verified Langfuse metadata propagation across refactored modules, added a unit
test spying on the editorial-workflow Langfuse surfaces, documented the rollback
ledger with actual branch SHAs, and tagged AE-0044/0045/0048 with
`high_risk_areas` metadata. No new wrappers were required — every changed public
signature already had a typed, explicit-parameter wrapper or did not change.

## Deprecation-Wrapper Inventory

| Function | Ticket | Signature changed? | Wrapper status | Location |
|----------|--------|--------------------|----------------|----------|
| `build_workflow_state_response` | AE-0044 | Yes (renamed to `build_editorial_workflow_state_response`) | **EXISTS** — `@deprecated` + `warnings.warn(DeprecationWarning)`, names new fn; typed params mirror new signature | `api/routes/carousels/editorial_workflow_routes_response.py:270` |
| `resolve_artifact_serving_paths` | AE-0043 | Yes (renamed to `resolve_and_reconcile_serving_paths`) | **EXISTS** — `warnings.warn(DeprecationWarning)`, names new fn; typed `project: CarouselProject` param | `application/services/carousel/artifact_path_resolver.py:104` |
| `resolve_presentation_review_from_state` | AE-0045 | **No** — public sig `(state)` unchanged; internals refactored to Chain-of-Responsibility | **NOT NEEDED** | `application/services/carousel/presentation_review.py:317` |
| `build_presentation_review_updates` | AE-0045 | **No** — public sig `(slide_drafts, *, translations_en, policy_version)` unchanged; extracted `_build_presentation_review_common` internally | **NOT NEEDED** | `application/services/carousel/presentation_review.py:190` |
| `build_presentation_review_updates_async` | AE-0045 | **No** — public sig unchanged; same internal extraction | **NOT NEEDED** | `application/services/carousel/presentation_review.py:214` |
| `validate_localized_slides` | AE-0046 | **No** — public sig `(localized_slides, *, policy_version)` unchanged; only extracted `_validate_single_slide` loop body | **NOT NEEDED** | `application/services/carousel/presentation_review.py:91` |
| `recover_project` | AE-0041 | Yes internally (`dry_run: bool` → `RunMode` via private `_RecoverProjectOptions`) | **NOT WARRANTED** — script-internal function, no external callers, CLI `--dry-run` flag preserved; a `dry_run: bool` shim would re-introduce the boolean trap AE-0041 removed | `scripts/recover_carousel_image_generations.py:234` |

**Conclusion:** Both genuinely-renamed public functions (AE-0043, AE-0044)
already have correctly typed deprecation wrappers with `DeprecationWarning`
messages naming the new function. No `*args: object` wrappers exist (no-`object`
rule honoured). No new wrappers added.

## Langfuse Trace Metadata Audit

Audited every module calling `get_langfuse_handler()` /
`propagate_attributes()` / `create_workflow_trace()`:
`agents/alter_ego_agent.py`, `agents/rag_agent.py`,
`application/tools/carousel/refine_copy.py`,
`application/services/blog_workflow_observability.py`,
`application/services/carousel/editorial_workflow_service.py`,
`monitoring_langfuse.py`, `infrastructure/monitoring_langfuse.py`.

The only refactored module touching Langfuse wiring is
`editorial_workflow_service.py` (changed by AE-0048 `59980df` and a later
PLR6301 `@staticmethod` pass). The diff was pure re-indentation plus bundling
positional args into a `PublishParams` command object — **no callback or
metadata field was dropped**.

**Verified metadata fields still propagated** (operational-equivalence
groundwork for the modularization plan):

| Field | Where wired | Surface |
|-------|-------------|---------|
| `project_id` | `start_workflow`, `resume_workflow`, event emission | `create_workflow_trace` config + `propagate_attributes` metadata |
| `phase` | `start_workflow` (`PHASE_RESEARCH`), human-review trace | `propagate_attributes` metadata + trace metadata |
| `user_id` | `start_workflow`, `resume_workflow` | `create_workflow_trace` config |
| `content_type` | `start_workflow`, `resume_workflow` (`CONTENT_TYPE_CAROUSEL`) | `create_workflow_trace` config |
| `agent_name` | agent/orchestrator layer (`rag_agent`, `alter_ego_agent`) — outside this service | agent callback metadata (unchanged by refactors) |

**Test added:**
`tests/unit/application/test_editorial_workflow_service.py::TestEditorialWorkflowServiceLangfuseTraceMetadata::test_start_workflow_propagates_langfuse_metadata`
spies on `create_workflow_trace` and `propagate_attributes` during
`start_workflow` and asserts `project_id`, `phase`, `user_id`, `content_type`
are passed through. `agent_name` is asserted to be a layer concern (documented in
the test docstring) rather than wired by this service, so it is covered at the
agent layer's existing traces, not duplicated here.

## Rollback Ledger

Execution order on branch `feat/wave-4-debt-patterns` (oldest → newest), with
the **revert order being the reverse**. Side-effect / compatibility ledger
format (mirrors the modularization plan's "Rollout and Rollback").

| Revert step | Ticket(s) | Commit SHA | `git revert` command | Side effects / caveats |
|-------------|-----------|-----------|----------------------|------------------------|
| 1 | AE-0048 (+ **AE-0045/0046 source refactor**) | `59980df` | `git revert 59980df` | **Entangled commit.** Reverting removes the blanket-ignore hardening AND the presentation-review Chain-of-Responsibility refactor (both landed here). Re-introduces blanket ruff/mypy ignores; restores the pre-CoR `resolve_presentation_review_from_state`. Revert FIRST. |
| 2 | AE-0044 builder + AE-0045/0046 **tests** | `b4d7261` | `git revert b4d7261` | Removes `build_editorial_workflow_state_response` builder + `_FIELD_MAPPING` and the AE-0044/0045/0046 pattern tests. The `build_workflow_state_response` deprecation alias disappears with it. |
| 3 | AE-0043 | `000eaa8` | `git revert 000eaa8` | Removes `resolve_artifact_serving_paths` deprecation alias + tests; callers must already use `resolve_and_reconcile_serving_paths` (rename itself predates this commit). |
| 4 | AE-0042 | `86bb9e4` | `git revert 86bb9e4` | Restores prior null-safety/exception-suppression behaviour in artifact manifest, image-generation records, presentation-review edits. |
| 5 | AE-0041 (+ AE-0049 CI) | `85f922f` | `git revert 85f922f` | Restores magic strings / nested ifs / `dry_run: bool` in `recover_*` scripts; reverts the AE-0049 CI gate hardening (mutation-weekly workflow, ruff-strict-changed, mutation-score-gate). Revert LAST. |

Notes:
- **AE-0047 (frontend modularization) has no commit on this branch** — nothing
  to revert.
- **AE-0046** has no standalone commit: its production change rides in `59980df`
  (refactor) with tests in `b4d7261`; covered by steps 1 and 2.
- Because `59980df` mixes AE-0048 with the AE-0045/0046 refactor, a clean
  AE-0048-only rollback is not possible via `git revert` of a single SHA; do a
  manual partial revert if only the CI ignores must roll back.

## Files Touched

- tests/unit/application/test_editorial_workflow_service.py (Langfuse metadata test)
- .agent/tasks/AE-0044/0045/0048 (high_risk_areas), AE-0050 (inventory/ledger)

## Test Evidence

```
mypy strict: Success (389); ruff: clean
pytest: 1649 passed, 2 skipped
validate_ticket 0044/0045/0048/0050: OK
```

## QA Report

Pending.

## Decision Log

- **No new deprecation wrappers required.** Every renamed public function
  (AE-0043, AE-0044) already had a typed wrapper with a `DeprecationWarning`
  naming the new function. AE-0045/0046 functions kept their public signatures
  (internal-only refactors), so no wrappers are warranted. `recover_project` is
  a private script function with no external callers; a public `dry_run: bool`
  shim would re-introduce the boolean trap AE-0041 removed — deliberately not
  added.
- **Wrappers are typed with explicit parameters** mirroring the new signatures;
  the `*args: object` example in Scope was intentionally NOT followed (violates
  the no-`object` rule per the Modularization Alignment note).
- **Langfuse metadata preserved.** Verified fields: `project_id`, `phase`,
  `user_id`, `content_type` (service layer) and `agent_name` (agent layer). The
  AE-0048 refactor of `editorial_workflow_service.py` was structural only and
  dropped no callbacks or metadata.
- **Rollback ledger** uses the plan's side-effect/compatibility format. The key
  caveat: AE-0048 and the AE-0045/0046 source refactor share commit `59980df`,
  so they cannot be reverted independently with a single `git revert`.

## Blockers

Blocked by: AE-0044, AE-0045, AE-0048

## Final Summary

Pending.
