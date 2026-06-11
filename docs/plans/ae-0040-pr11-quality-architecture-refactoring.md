# Epic: AE-0040 — PR #11 Code Quality and Architecture Refactoring

> **Tier:** T3
> **Area:** Cross-cutting (Backend + Frontend)
> **Status:** Planning
> **Created:** 2026-06-10

## Overview

Systematic remediation of all 23 code review comments from PR #11 and 7 CI gate failures. Root cause: AI-generated code was merged without enforcing project rules (max-args=3, no magic strings, early returns, type safety), and blanket ignores in `pyproject.toml` hid violations. This epic eliminates technical debt, installs permanent CI guards, and refactors fragile architectural patterns.

## Structure

| Ticket | Theme | Tier | Area | Dependencies |
|--------|-------|------|------|-------------|
| AE-0041 | Magic Strings, Early Returns, Boolean Trap → Enum | T2 | Backend | None |
| AE-0042 | Null-Safety, Exception Suppression, Safe Access | T2 | Backend | None |
| AE-0043 | Segregate Overloaded Functions (persist, paths) | T2 | Backend | None |
| AE-0044 | Builder Pattern for `build_workflow_state_response` | T2 | Backend | AE-0041 (constants) |
| AE-0045 | Strategy/Chain-of-Responsibility + async/sync dedup | T2 | Backend | AE-0041 (constants) |
| AE-0046 | Validation Refactor for `ContentSlideCopy` | T2 | Backend | AE-0041 (constants) |
| AE-0047 | Frontend Modularization (types, constants, spinner) | T2 | Frontend | None |
| AE-0048 | Remove Blanket Ignores + Mypy Hardening | T3 | Backend/CI | AE-0041 through AE-0046 |
| AE-0049 | CI Gate Improvements | T2 | CI/DevOps | AE-0048 |
| AE-0050 | Rollback, Migration, and Observability Safeguards | T2 | Cross-cutting | AE-0044, AE-0045, AE-0048 |

## Execution Order

```
Week 1 ─┬─ AE-0041 (Magic strings, early returns, boolean→enum)
         ├─ AE-0042 (Null-safety, exception suppression)
         ├─ AE-0043 (Segregate overloaded functions)
         └─ AE-0047 (Frontend modularization)
               ↓
Week 2 ─┬─ AE-0044 (Builder pattern — API response builder)
         ├─ AE-0045 (Strategy pattern + Chain-of-Responsibility)
         └─ AE-0046 (Validation refactor)
               ↓
Week 3 ─┬─ AE-0050 (Rollback safeguards, deprecation wrappers)
         └─ AE-0049 (CI gate improvements)
               ↓
Week 4 ─── AE-0048 (Remove blanket ignores — requires all above)
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

For blanket ignore removal (AE-0048): if CI stays red > 4 hours, revert the PR and split into smaller increments (one ruff rule per commit).
