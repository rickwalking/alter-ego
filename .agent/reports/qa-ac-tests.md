# Acceptance Criteria & Tests Subagent Report

## Findings
| Severity | Finding | File:Line | Evidence |
|----------|---------|-----------|----------|
| 🔴 | AE-0039 release gate NOT MET — no clean seven-slide PT/EN E2E publish run, contact sheets, or mutation-score evidence | `.agent/reports/AE-0028.qa-fixes.qa.md:88` | Epic release AC still open; prior QA pass blocked |
| 🔴 | AE-0034 structured editing AC NOT MET — content-phase-review is read-only; no `expected_version` on structured content approve/refine | `.agent/reports/AE-0028.qa-fixes.qa.md:98` | `content-phase-review.tsx` lacks editable union payload submit |
| 🟠 | 21 new carousel modules lack dedicated unit test files | `tests/unit/application/` | `artifact_build_support`, `artifact_build_types`, `artifact_manifest`, `artifact_path_resolver`, `creator_asset_service`, `editorial_distribution_constants`, `editorial_subagent`, `editorial_visual_pipeline`, `editorial_workflow_events`, `editorial_workflow_service_helpers`, `image_prompt_package`, `legacy_presentation_regeneration`, `localized_slide_builder`, `phase_subagents`, `presentation_copy_repair`, `presentation_policy_types`, `presentation_validation_fields`, `refinement_service`, `types`, `workflow_state` |
| 🟠 | `editorial_workflow_service.py` coverage below 90% target | `src/rag_backend/application/services/carousel/editorial_workflow_service.py` | 85% (126 stmts, 19 miss) — missing lines 132-142, 144-162, 182, 186, 198, 279, 296-300 |
| 🟠 | `artifact_health.py` coverage below 90% target | `src/rag_backend/application/services/carousel/artifact_health.py` | 88% (225 stmts, 27 miss) — missing lines 144, 157, 164, 200-222, 311, 365, 371-372 |
| 🟠 | `presentation_review.py` exceeds 400-line limit | `src/rag_backend/application/services/carousel/presentation_review.py` | 435 lines (CLAUDE.md max 400 lines) |
| 🟠 | `presentation_policy.py` exceeds 400-line limit | `src/rag_backend/application/services/carousel/presentation_policy.py` | 414 lines (CLAUDE.md max 400 lines) |
| 🟠 | `slide_styles.py` exceeds 400-line limit | `src/rag_backend/.../slide_styles.py` | 719 lines (pre-existing debt, still over limit) |
| 🟠 | Mutation testing not run on changed modules | ADR-005 | Incremental `mutmut`/`Stryker` skipped for this fix pass |
| 🟡 | `presentation_review.py` coverage below 90% target | `src/rag_backend/application/services/carousel/presentation_review.py` | 86% (94 stmts, 13 miss) — missing lines 85, 110, 186-196, 216, 253-257 |
| 🟡 | `artifact_path_safety.py` coverage below 95% (close to 90%) | `src/rag_backend/application/services/carousel/artifact_path_safety.py` | 93% (28 stmts, 2 miss) — missing lines 31, 37 |
| 🟡 | Creator asset per-owner dedup lacks dedicated unit test | `creator_asset_service.py` | Migration `0009` exists but no test proving cross-owner duplicate upload succeeds |

## Evidence

### Backend test run
```bash
cd backend && uv run pytest --tb=short -q 2>&1 | tail -10
# =========== 1192 passed, 2 skipped, 18 warnings in 94.16s (0:01:34) ============
```

### Backend coverage (total)
```bash
cd backend && uv run pytest --cov=rag_backend --tb=short -q 2>&1 | tail -20
# TOTAL                                                                                   15843   3387    79%
# =========== 1192 passed, 2 skipped, 18 warnings in 130.74s (0:02:10) ===========
```

### Frontend test run
```bash
cd frontend && npm run test -- --run 2>&1 | tail -10
#  Test Files  69 passed (69)
#       Tests  788 passed (788)
#    Start at  22:19:15
#    Duration  17.62s (transform 49.64s, setup 61.07s, import 70.60s, tests 23.36s, environment 62.88s)
```

### Missing test files for new carousel modules
```bash
for f in backend/src/rag_backend/application/services/carousel/*.py; do
  base=$(basename "$f" .py)
  if [ ! -f "backend/tests/unit/application/test_${base}.py" ]; then
    echo "MISSING: $base"
  fi
done
# MISSING: artifact_build_support
# MISSING: artifact_build_types
# MISSING: artifact_manifest
# MISSING: artifact_path_resolver
# MISSING: creator_asset_service
# MISSING: editorial_distribution_constants
# MISSING: editorial_subagent
# MISSING: editorial_visual_pipeline
# MISSING: editorial_workflow_events
# MISSING: editorial_workflow_service_helpers
# MISSING: image_prompt_package
# MISSING: legacy_presentation_regeneration
# MISSING: localized_slide_builder
# MISSING: phase_subagents
# MISSING: presentation_copy_repair
# MISSING: presentation_policy_types
# MISSING: presentation_validation_fields
# MISSING: refinement_service
# MISSING: types
# MISSING: workflow_state
```

### New module coverage
```bash
cd backend && uv run pytest --cov=rag_backend.application.services.carousel.artifact_health \
  --cov=rag_backend.application.services.carousel.editorial_workflow_service \
  --cov=rag_backend.application.services.carousel.presentation_validation \
  --cov=rag_backend.application.services.carousel.presentation_review \
  --cov=rag_backend.application.services.carousel.artifact_path_safety \
  --cov-report=term-missing -q 2>&1 | tail -30

# Name                                                                          Stmts   Miss  Cover   Missing
# -----------------------------------------------------------------------------------------------------------
# src/rag_backend/application/services/carousel/artifact_health.py                225     27    88%   144, 157, 164, 200-222, 311, 365, 371-372
# src/rag_backend/application/services/carousel/artifact_path_safety.py             28      2    93%   31, 37
# src/rag_backend/application/services/carousel/editorial_workflow_service.py     126     19    85%   132-142, 144-162, 182, 186, 198, 279, 296-300
# src/rag_backend/application/services/carousel/presentation_review.py             94     13    86%   85, 110, 186-196, 216, 253-257
# src/rag_backend/application/services/carousel/presentation_validation.py         85      2    98%   136, 278
# -----------------------------------------------------------------------------------------------------------
# TOTAL                                                                           558     63    89%
# =========== 1192 passed, 2 skipped, 18 warnings in 126.72s (0:02:06) ===========
```

### Prior AE-0028 gaps (from `.agent/reports/AE-0028.qa.md` and `.agent/reports/AE-0028.qa-fixes.qa.md`)
- **AE-0039** — No captured clean seven-slide PT/EN E2E publish run, contact sheets, mutation scores, or slash-command smoke evidence. Epic AC #5 and AE-0039 AC #1/#4 NOT MET.
- **AE-0034** — Structured editing + versioned content submit (`expected_version` on content approve/refine with union payload) NOT MET. `content-phase-review.tsx` is read-only.
- **File-size debt** — `presentation_review.py` 435 lines, `presentation_policy.py` 414 lines, `slide_styles.py` 719 lines (all >400 line CLAUDE.md limit).
- **Mutation testing** — Incremental `mutmut`/`Stryker` not executed for this pass (ADR-005 target 70%+ on business logic unverified).

## Test Coverage Summary
| Module | Coverage | Target |
|--------|----------|--------|
| `artifact_health.py` | 88% | 90% |
| `artifact_path_safety.py` | 93% | 90% |
| `editorial_workflow_service.py` | 85% | 90% |
| `presentation_review.py` | 86% | 90% |
| `presentation_validation.py` | 98% | 90% |
| `rag_backend` (total) | 79% | 90% |

## Summary
- **Blockers:** 2
  - AE-0039 release evidence gap (E2E/contact sheets/mutation scores)
  - AE-0034 structured editing AC not implemented (read-only review UI)
- **Warnings:** 8
  - 21 new carousel modules without dedicated unit tests
  - `editorial_workflow_service.py` 85% coverage (below 90%)
  - `artifact_health.py` 88% coverage (below 90%)
  - `presentation_review.py` 435 lines (exceeds 400-line limit)
  - `presentation_policy.py` 414 lines (exceeds 400-line limit)
  - `slide_styles.py` 719 lines (exceeds 400-line limit)
  - Mutation testing skipped for this pass
  - Creator asset per-owner dedup lacks dedicated unit test
- **Suggestions:** 3
  - Add tests for `presentation_review.py` missing lines (85, 110, 186-196, 216, 253-257) to push coverage to 90%+
  - Add tests for `editorial_workflow_service.py` missing lines (132-162, 182, 186, 198, 279, 296-300) to push coverage to 90%+
  - Run incremental `mutmut` on `artifact_path_safety`, `presentation_review_repair`, `content-phase-review` utils to verify ADR-005 target
