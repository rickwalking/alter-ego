# Epic: AE-0040 — PR #11 Code Quality and Architecture Refactoring

> **Tier:** T3
> **Area:** Cross-cutting (Backend + Frontend)
> **Status:** Active — Partially Implemented (AE-0048 merged; 14 subtickets still open)
> **Created:** 2026-06-10
> **Updated:** 2026-06-11

## Overview

Systematic remediation of all **24 unresolved code review comments** from PR #11 and **7 CI gate failures**. Root cause: AI-generated code was merged without enforcing project rules (max-args=3, no magic strings, early returns, type safety), and blanket ignores in `pyproject.toml` hid violations. This epic eliminates technical debt, installs permanent CI guards, and refactors fragile architectural patterns.

**Why some comments were not converted to tickets initially:**
The original plan grouped 23+ comments into 10 thematic tickets (AE-0041–AE-0050). This was too coarse — specific file-level issues were absorbed into vague themes without discrete, actionable items per comment. For example, "move classes in `strategies.py`" and "complex function in `recover_carousel_image_generations.py`" were never individually tracked. This revision enumerates **every unresolved PR comment** as a distinct ticket with clear acceptance criteria.

## PR Comment Inventory — Complete Mapping

All 24 unresolved comments from `rickwalking`'s PR #11 review, mapped to tickets:

| # | File | Line | Comment Body | Ticket | Status |
|---|------|------|--------------|--------|--------|
| 1 | `backend/scripts/recover_carousel_image_generations.py` | 126 | "issue: very complex if statements. Inner statements, prefer early return" | AE-0051 | Pending |
| 2 | `backend/scripts/recover_carousel_image_generations.py` | 104 | "very complex function" | AE-0051 | Pending |
| 3 | `backend/scripts/recover_carousel_image_generations.py` | 108 | "using boolean as a parameter is a antipattern" | AE-0051 | Pending |
| 4 | `backend/scripts/regenerate_carousel_presentation.py` | 94 | "inner if statement. Use dictionaries instead of complex number of if statements" | AE-0052 | Pending |
| 5 | `backend/scripts/repair_workflow_malformed_drafts.py` | 69 | "magic string" | AE-0053 | Pending |
| 6 | `backend/scripts/repair_workflow_malformed_drafts.py` | 62 | "very long/complex function" | AE-0053 | Pending |
| 7 | `backend/scripts/repair_workflow_malformed_drafts.py` | 155 | "inner if statement" | AE-0053 | Pending |
| 8 | `backend/src/rag_backend/api/routes/carousels/editorial_workflow_routes_response.py` | 22 | "very complex function. Let's think about the best architect solution. Maybe a Builder pattern. Create a plan to resolve this" | AE-0044 | Pending |
| 9 | `backend/src/rag_backend/api/routes/carousels/strategies.py` | 29 | "move these classes to a new file" | AE-0054 | Pending |
| 10 | `backend/src/rag_backend/application/services/carousel/artifact_manifest.py` | 171 | "is it safe to access all these properties without checking? let's think about a better architect solution" | AE-0057 | Pending |
| 11 | `backend/src/rag_backend/application/services/carousel/artifact_path_resolver.py` | 46 | "inner if statements" | AE-0055 | Pending |
| 12 | `backend/src/rag_backend/application/services/carousel/creator_asset_validation.py` | 94 | "magic string" | AE-0058 | Pending |
| 13 | `backend/src/rag_backend/application/services/carousel/editorial_distribution_persist.py` | 44 | "very large function" | AE-0059 | Pending |
| 14 | `backend/src/rag_backend/application/services/carousel/image_generation_records.py` | 102 | "inner if statement" | AE-0060 | Pending |
| 15 | `backend/src/rag_backend/application/services/carousel/presentation_review.py` | 46 | "very complex function" | AE-0061 | Pending |
| 16 | `backend/src/rag_backend/application/services/carousel/presentation_review_edits.py` | 69 | "assignment without checking for nullable values" | AE-0062 | Pending |
| 17 | `backend/src/rag_backend/domain/models/carousel_presentation.py` | 173 | "This is a if hell. So many inner if statements. This is not manageable, this will cause a lot of issues to tests" | AE-0046 | Pending |
| 18 | `backend/src/rag_backend/domain/models/carousel_presentation_adapters.py` | 78 | "magic strings" | AE-0063 | Pending |
| 19 | `backend/src/rag_backend/domain/models/carousel_presentation_adapters.py` | 102 | "magic strings, very complex if statements chain" | AE-0063 | Pending |
| 20 | `backend/src/rag_backend/application/services/carousel/presentation_validation_fields.py` | 270 | "magic strings" | AE-0064 | Pending |
| 21 | `frontend/src/app/dashboard/create/workspace/create-workflow-controls.tsx` | 14 | "move interface to its own file" | AE-0065 | Pending |
| 22 | `frontend/src/features/create/components/workflow-failed-card.tsx` | 14 | "move constants to its own file (constants)" | AE-0066 | Pending |
| 23 | `frontend/src/features/publish/components/regenerate-strategy-section.tsx` | 21 | "constants, interfaces and utils functions to its own file" | AE-0067 | Pending |
| 24 | `frontend/src/features/publish/components/regenerate-strategy-section.tsx` | 78 | "Create a spinner/loading component to reuse. Use React Suspense." | AE-0068 | Pending |

## CI Gate Status

| Gate | Status | Notes |
|------|--------|-------|
| agent / validate tickets | ❌ FAILURE | 20 tasks in Review/QaRunning missing QA reports |
| backend / Lint & Format | ❌ FAILURE | AE-0048 fixed 162 violations; ongoing refactors introduced new ones |
| backend / Strict Diff | ❌ FAILURE | Some refactored functions still exceed args/complexity limits |
| backend / Type Check | ❌ FAILURE | mypy --strict fails on refactored code |
| backend / Architecture | ✅ SUCCESS | Fixed application→api violations |
| backend / Docstrings | ✅ SUCCESS | |
| backend / Security | ❌ FAILURE | S105/hardcoded-password on new domain/constants/chat_stream.py |
| backend / Test & Coverage | ❌ FAILURE | Tests fail or diff coverage below 75% |
| backend / Dead Code | ✅ SUCCESS | |
| backend / Mutation (advisory) | ⏭️ SKIPPED | Skipped due to prior failures |
| Frontend gates | ❌ FAILURE | Mutation advisory failures |

## Ticket Structure

### Backend Source Code — Architecture & Design Patterns

| Ticket | Theme | Tier | Area | Dependencies | PR # Comments |
|--------|-------|------|------|-------------|------|
| AE-0041 | Magic Strings, Early Returns, Boolean Trap → Enum | T2 | Backend | None | — |
| AE-0042 | Null-Safety, Exception Suppression, Safe Access | T2 | Backend | None | — |
| AE-0043 | Segregate Overloaded Functions (persist, paths) | T2 | Backend | None | — |
| AE-0044 | Builder Pattern for `build_workflow_state_response` | T2 | Backend | AE-0041 | #8 |
| AE-0045 | Strategy/Chain-of-Responsibility + async/sync dedup | T2 | Backend | AE-0041 | — |
| AE-0046 | Validation Refactor for `ContentSlideCopy` | T2 | Backend | AE-0041 | #17 |
| AE-0054 | Move strategy classes in `strategies.py` to dedicated file | T1 | Backend | None | #9 |
| AE-0055 | Flatten nested ifs in `artifact_path_resolver.py` | T1 | Backend | None | #11 |
| AE-0056 | Add Builder for `build_workflow_state_response` (+ test) | T2 | Backend | None | merged into AE-0044 |
| AE-0057 | Null safety for property access in `artifact_manifest.py` | T2 | Backend | None | #10 |
| AE-0058 | Extract magic strings in `creator_asset_validation.py` | T1 | Backend | None | #12 |
| AE-0059 | Split large function in `editorial_distribution_persist.py` | T2 | Backend | None | #13 |
| AE-0060 | Flatten inner ifs in `image_generation_records.py` | T1 | Backend | None | #14 |
| AE-0061 | Reduce complexity in `presentation_review.py` | T2 | Backend | None | #15 |
| AE-0062 | Null-safe assignment in `presentation_review_edits.py` | T1 | Backend | None | #16 |
| AE-0063 | Extract magic strings + simplify if chain in `carousel_presentation_adapters.py` | T1 | Backend | None | #18, #19 |
| AE-0064 | Extract magic strings in `presentation_validation_fields.py` | T1 | Backend | None | #20 |

### Scripts — Recovery, Repair, Regeneration

| Ticket | File | Comments Addressed | Tier | Area |
|--------|------|-------------------|------|------|
| AE-0051 | `recover_carousel_image_generations.py` | #1, #2, #3 — complex function, nested ifs, boolean trap | T1 | Backend/Scripts |
| AE-0052 | `regenerate_carousel_presentation.py` | #4 — if chain → dict dispatch | T1 | Backend/Scripts |
| AE-0053 | `repair_workflow_malformed_drafts.py` | #5, #6, #7 — magic strings, long function, nested ifs | T2 | Backend/Scripts |

### Frontend Modularization

| Ticket | Component | Comments Addressed | Tier | Area |
|--------|-----------|-------------------|------|------|
| AE-0065 | `create-workflow-controls.tsx` — move interface | #21 | T1 | Frontend |
| AE-0066 | `workflow-failed-card.tsx` — move constants | #22 | T1 | Frontend |
| AE-0067 | `regenerate-strategy-section.tsx` — split constants, types, utils | #23 | T1 | Frontend |
| AE-0068 | Create reusable `<Spinner>` with React Suspense | #24 | T2 | Frontend |

### CI & QA

| Ticket | Theme | Tier | Area | Dependencies |
|--------|-------|------|------|-------------|
| AE-0048 | Remove Blanket Ignores + Mypy Hardening | T3 | Backend/CI | All code-fix tickets |
| AE-0049 | CI Gate Improvements (Strict Diff hardening) | T2 | CI/DevOps | AE-0048 |
| AE-0050 | Rollback, Migration, and Observability Safeguards | T2 | Cross-cutting | AE-0044, AE-0045, AE-0048 |
| AE-0069 | Generate QA reports for all Review-status tasks | T1 | QA | None |

## Execution Order

```
Phase 1 — Quick Wins (T1, no deps)
├─ AE-0054 (Move strategy classes to file)
├─ AE-0055 (Flatten ifs in artifact_path_resolver)
├─ AE-0058 (Magic strings in creator_asset_validation)
├─ AE-0060 (Flatten ifs in image_generation_records)
├─ AE-0062 (Null-safe assignment in presentation_review_edits)
├─ AE-0063 (Magic strings in carousel_presentation_adapters)
├─ AE-0064 (Magic strings in presentation_validation_fields)
├─ AE-0051 (Script: recover_carousel_image_generations)
├─ AE-0052 (Script: regenerate_carousel_presentation)
├─ AE-0065 (Frontend: move interface)
├─ AE-0066 (Frontend: move constants)
├─ AE-0067 (Frontend: split regenerate-strategy-section)
└─ AE-0069 (Generate QA reports)

Phase 2 — Moderate Refactors (T2)
├─ AE-0053 (Script: repair_workflow_malformed_drafts)
├─ AE-0059 (Split function in editorial_distribution_persist)
├─ AE-0061 (Reduce complexity in presentation_review)
├─ AE-0068 (Frontend: Spinner component)
└─ AE-0057 (Null safety in artifact_manifest)

Phase 3 — Architecture Patterns (T2, may need planning)
├─ AE-0041 (Magic strings, early returns, boolean→enum)
├─ AE-0042 (Null-safety, exception suppression)
├─ AE-0043 (Segregate functions)
├─ AE-0044 (Builder pattern)
├─ AE-0045 (Strategy/CoR)
└─ AE-0046 (Validation refactor)

Phase 4 — CI & Observability
├─ AE-0050 (Rollback safeguards)
├─ AE-0049 (CI gate improvements)
└─ AE-0048 (Blanket ignores — already merged)
```

## Migration Strategy

Functions with changed signatures (e.g., `validate_localized_slides`, `build_presentation_review_updates`) keep a `@deprecated` wrapper for one sprint:

```python
import warnings

def old_function_name(*args: object, **kwargs: object) -> object:
    warnings.warn(
        "old_function_name is deprecated, use new_function_name",
        DeprecationWarning,
        stacklevel=2,
    )
    return new_function_name(*args, **kwargs)
```

All deprecation wrappers will be removed at the end of the next sprint after AE-0048 is merged.

## Rollback Plan

Each ticket MUST be a reversible PR. If CI breaks:
1. `git revert <merge-commit>` on the offending PR
2. Open a fixing PR with the issue documented
3. Only re-merge after `ruff check` + `mypy` + `pytest` pass

## What Was Already Done (AE-0048)

- 162 pre-existing ruff violations fixed (zero per-file-ignores added)
- Application→API architecture violations fixed (SSE constants → domain; design tokens → application)
- Circular import in `generate_carousel.py` resolved
- Stale import-linter ignore removed
