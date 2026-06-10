# Mutation Testing Subagent Report

## Findings
| Severity | Finding | Module | Score |
|----------|---------|--------|-------|
| 🔴 | All surviving mutants in target modules — tests are too shallow to catch boundary/negation mutations | artifact_path_safety | 81% |
| 🔴 | High survival rate (24/76) on presentation_review_repair — locale repair logic and slide repair logic need stronger assertions | presentation_review_repair | 68% |
| 🟡 | artifact_index_reconciler scores above threshold but still has 5 surviving mutants in index reconciliation | artifact_index_reconciler | 81% |
| 🔴 | Frontend Stryker cannot run — vitest fails to discover related tests for mutated files | frontend (all) | N/A |
| 🟡 | Baseline test flakiness required `--ignore` workarounds for file-path tests in mutants directory | backend baseline | red |

## Evidence

### Backend mutmut (target modules only)
```bash
# Configuration check
$ cd backend && grep -A 20 "mutmut" pyproject.toml
    "mutmut>=3.5.0",
    ...
[tool.mutmut]
paths_to_mutate = [ ... ]  # 15 files configured

# Run on target set (3 files)
$ cd backend && uv run mutmut run --max-children=4
    done in 295ms (3 files mutated, 0 ignored, 0 unmodified)
Running mutation testing
    done
134/134  🎉 99 🫥 0  ⏰ 0  🤔 0  🙁 35  🔇 0  🧙 0
29.13 mutations/second

# Per-module breakdown
$ uv run mutmut results --all true
artifact_path_safety:      31 total, 6 survived, 25 killed  → 80.6%
presentation_review_repair: 76 total, 24 survived, 52 killed → 68.4%
artifact_index_reconciler:  27 total, 5 survived, 22 killed  → 81.5%
```

### Frontend Stryker
```bash
$ cd frontend && npx stryker run --mutate src/lib/client-api.ts
INFO DryRunExecutor Starting initial test run (vitest test runner with "off" coverage analysis).
WARN VitestTestRunner Vitest failed to find test files related to mutated files.
ERROR Stryker No tests were executed. Stryker will exit prematurely.
ConfigError: No tests were executed.
```

### Baseline issues encountered
- `test_presentation_contract_alignment.py` and `test_bilingual_export.py` fail in the mutmut sandbox due to relative file-path lookups (`skills/runtime/...` YAML contract files not copied into the `mutants` directory).
- Required temporary `pyproject.toml` modification adding `--ignore` flags for those two tests to allow the baseline to pass.
- `setup.cfg` contains a `runner` key that is not supported by mutmut 3.5.0 and is therefore ignored.

## Summary
- **Modules tested**: 3 (backend) | 0 (frontend — Stryker blocked)
- **Mutation scores**:
  - `artifact_path_safety`: 81% (6/31 survived)
  - `presentation_review_repair`: 68% (24/76 survived)
  - `artifact_index_reconciler`: 81% (5/27 survived)
  - **Overall**: 73.9% (35/134 survived)
- **Baseline status**: 🔴 red — required `--ignore` hacks to bypass file-path tests that break in the mutants sandbox
- **Time taken**: ~2 min
- **Frontend status**: 🔴 Stryker cannot execute due to vitest `related` test discovery failure; no mutation score produced

**Recommendation**: Strengthen unit tests for `presentation_review_repair` (below 70% threshold), fix the `skills/runtime/...` contract path resolution so baseline tests pass without `--ignore`, and investigate the Stryker/vitest `related` test discovery issue in the frontend.
