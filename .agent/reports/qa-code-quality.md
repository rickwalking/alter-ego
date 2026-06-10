# Code Quality Audit Subagent Report

## Findings
| Severity | Finding | File:Line | Rule |
|----------|---------|-----------|------|
| 🟡 | Import block is un-sorted or un-formatted | src/rag_backend/api/routes/carousels/creator_assets.py:3 | I001 |
| 🟡 | `__all__` is not sorted | src/rag_backend/application/services/carousel/editorial_distribution_constants.py:18 | RUF022 |
| 🟡 | Import block is un-sorted or un-formatted | src/rag_backend/application/services/carousel/editorial_distribution_pack.py:3 | I001 |
| 🟡 | Expected 2 blank lines, found 1 | src/rag_backend/application/services/carousel/editorial_distribution_pack.py:78 | E302 |
| 🟠 | Prefer `TypeError` exception for invalid type | src/rag_backend/application/services/carousel/editorial_distribution_pack.py:321 | TRY004 |
| 🟡 | Import block is un-sorted or un-formatted | src/rag_backend/application/services/carousel/editorial_workflow_generators.py:3 | I001 |
| 🟡 | Import block is un-sorted or un-formatted | src/rag_backend/application/services/carousel/localized_slide_builder.py:3 | I001 |
| 🟡 | Return the condition directly instead of needless bool | src/rag_backend/application/services/carousel/malformed_draft_normalizer.py:178 | SIM103 |
| 🔴 | Calling setState synchronously within an effect can trigger cascading renders | frontend/src/app/dashboard/create/workspace/create-workflow-panel.tsx:116:5 | react-hooks/set-state-in-effect |

## Evidence

### Backend Ruff (agents, services, routes)
```bash
cd backend && uv run ruff check src/rag_backend/api/routes/carousels/ src/rag_backend/application/services/carousel/ src/rag_backend/application/services/carousel_template/ src/rag_backend/agents/ --statistics

4	I001  	[*] unsorted-imports
1	E302  	[*] blank-lines-top-level
1	RUF022	[*] unsorted-dunder-all
1	SIM103	[ ] needless-bool
1	TRY004	[ ] type-check-without-type-error
Found 8 errors.
[*] 6 fixable with the `--fix` option (1 hidden fix can be enabled with the `--unsafe-fixes` option).
```

### Backend Ruff (domain constants/models)
```bash
cd backend && uv run ruff check src/rag_backend/domain/constants/ src/rag_backend/domain/models/ --statistics

(no output)
```

### Backend Mypy
```bash
cd backend && MYPYPATH=src uv run mypy --explicit-package-bases -p rag_backend.application.services.carousel -p rag_backend.application.services.carousel_template 2>&1 | tail -20

pyproject.toml: note: unused section(s): module = ['rag_backend.agents.*', ...]
Success: no issues found in 2 source files
```

### Files > 400 lines
```bash
cd backend && find src/rag_backend/application/services/carousel/ src/rag_backend/application/services/carousel_template/ -name "*.py" -exec wc -l {} + | sort -rn | head -20

   486 src/rag_backend/application/services/carousel/editorial_distribution_pack.py
   410 src/rag_backend/application/services/carousel/artifact_health.py
   404 src/rag_backend/application/services/carousel/editorial_workflow_support.py
   400 src/rag_backend/application/services/carousel/editorial_workflow_service.py
   386 src/rag_backend/application/services/carousel/phase_artifact_runner.py
   384 src/rag_backend/application/services/carousel/nodes/images.py
   341 src/rag_backend/application/services/carousel/presentation_policy.py
   315 src/rag_backend/application/services/carousel/presentation_validation.py
   313 src/rag_backend/application/services/carousel/legacy_presentation_regeneration.py
   293 src/rag_backend/application/services/carousel/presentation_validation_fields.py
   290 src/rag_backend/application/services/carousel_template/css/base.py
   289 src/rag_backend/application/services/carousel_template/css/slide_styles_shell.py
   282 src/rag_backend/application/services/carousel/artifact_build_support.py
   276 src/rag_backend/application/services/carousel/presentation_review.py
   264 src/rag_backend/application/services/carousel_template/css/slide_styles_closing.py
   257 src/rag_backend/application/services/carousel_template/css/slide_template/html_template.py
   252 src/rag_backend/application/services/carousel/editorial_workflow_service_helpers.py
   239 src/rag_backend/application/services/carousel/malformed_draft_normalizer.py
   239 src/rag_backend/application/services/carousel/artifact_build_service.py
```

### Frontend Lint
```bash
cd frontend && npm run lint 2>&1 | tail -20

/home/pmarins/projects/alter-ego/frontend/src/app/dashboard/create/workspace/create-workflow-panel.tsx
  116:5  error  Error: Calling setState synchronously within an effect can trigger cascading renders
  react-hooks/set-state-in-effect

✖ 1 problem (1 error, 0 warnings)
```

### Frontend Typecheck
```bash
cd frontend && npm run typecheck 2>&1 | tail -20

> alter-ego-frontend@0.1.0 typecheck
> tsc --noEmit

(no errors)
```

## Summary
- **Blockers:** 1
  - Frontend lint error (`react-hooks/set-state-in-effect` in `create-workflow-panel.tsx:116`)
- **Warnings:** 1
  - `TRY004` (raise `ValueError` instead of `TypeError`) in `editorial_distribution_pack.py:321`
- **Suggestions:** 7
  - 4 `I001` unsorted imports
  - 1 `E302` missing blank line
  - 1 `RUF022` unsorted `__all__`
  - 1 `SIM103` needless bool
- **Files > 400 lines:**
  - `src/rag_backend/application/services/carousel/editorial_distribution_pack.py` (486 lines)
  - `src/rag_backend/application/services/carousel/artifact_health.py` (410 lines)
  - `src/rag_backend/application/services/carousel/editorial_workflow_support.py` (404 lines)
  - `src/rag_backend/application/services/carousel/editorial_workflow_service.py` (400 lines)
