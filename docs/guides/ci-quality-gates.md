# CI Quality Gates

Deterministic quality enforcement for **backend** and **frontend**, grouped by project. These workflows implement the CI subset described in [QA Checkpoints §7](./qa-checkpoints.md#7-cicd-quality-gates).

The full `/qa-agent` skill remains **on-demand** for acceptance-criteria validation, deep security review, and architecture judgment.

## Workflows

| Project | Workflow file | Triggers |
|---------|---------------|----------|
| Backend | [`.github/workflows/backend-quality-gates.yml`](../../.github/workflows/backend-quality-gates.yml) | `backend/**`, `scripts/ci/**` |
| Frontend | [`.github/workflows/frontend-quality-gates.yml`](../../.github/workflows/frontend-quality-gates.yml) | `frontend/**`, `scripts/ci/**` |

Both workflows run on **all pull requests** (any base branch) when matching paths change.

## Backend jobs

| Job name | Purpose |
|----------|---------|
| `backend / Lint & Format` | Ruff format + lint on `src/` |
| `backend / Strict Diff (args & complexity)` | `PLR0913`, `C901`, `PLR0912` on changed Python files only |
| `backend / Type Check` | mypy |
| `backend / Architecture` | import-linter |
| `backend / Docstrings` | interrogate ≥80% |
| `backend / Security` | bandit + pip-audit |
| `backend / Test & Coverage` | pytest + diff-cover ≥75% vs `main` |
| `backend / Dead Code` | vulture |
| `backend / Mutation (advisory)` | mutmut (non-blocking) |

## Frontend jobs

| Job name | Purpose |
|----------|---------|
| `frontend / Lint` | ESLint errors repo-wide (`npm run lint` → `--quiet`) |
| `frontend / Lint (changed)` | Strict ESLint on PR diff (`npm run lint:changed` → `--max-warnings=0`) |
| `frontend / Type Check` | `tsc --noEmit` |
| `frontend / Test` | vitest |
| `frontend / Format` | Prettier |
| `frontend / Security` | `npm audit --audit-level=high` |
| `frontend / Mutation (advisory)` | Stryker (non-blocking) |

## Diff-scoped scripts

| Script | Used by |
|--------|---------|
| [`scripts/ci/changed-backend-files.sh`](../../scripts/ci/changed-backend-files.sh) | Backend strict ruff |
| [`scripts/ci/ruff-strict-changed.sh`](../../scripts/ci/ruff-strict-changed.sh) | Backend strict diff job |
| [`scripts/ci/changed-frontend-files.sh`](../../scripts/ci/changed-frontend-files.sh) | Frontend changed lint |
| [`scripts/ci/eslint-changed.mjs`](../../scripts/ci/eslint-changed.mjs) | Frontend changed lint job |
| [`scripts/ci/post-pr-quality-comment.sh`](../../scripts/ci/post-pr-quality-comment.sh) | PR summary on gate failure |

## PR feedback

1. **reviewdog** — inline file/line comments on PRs when lint fails (Ruff, ESLint).
2. **`post-pr-quality-comment.sh`** — summary comment linking to QA checkpoints when a blocking job fails.
3. **Mutation advisory** — non-blocking jobs post a summary; they do not block merge.

## Local commands

```bash
# Backend
cd backend && uv run ruff check src/ && uv run mypy rag_backend/ --explicit-package-bases
bash scripts/ci/ruff-strict-changed.sh

# Frontend
cd frontend && npm run lint && npm run lint:changed && npm run typecheck
```

## Pre-commit

[`.pre-commit-config.yaml`](../../.pre-commit-config.yaml) runs:

- Backend: ruff, gitleaks, import-linter, vulture
- Frontend: ESLint (errors only), TypeScript (on `frontend/src/**` changes)

## ESLint rollout policy

| Scope | Policy |
|-------|--------|
| Repo-wide | Errors only (`eslint --quiet`) — unused vars, hooks, explicit `any`, etc. |
| Changed files | Strict (`--max-warnings=0`) — page size, complexity, TanStack Query rules |
| `page.tsx` global | Warnings for `max-lines` / `max-lines-per-function` (legacy pages) |
| `page.tsx` in PR diff | Enforced as errors via `lint:changed` |

## Branch protection (GitHub Settings)

Require these status checks on `main`:

**Backend**

- `backend / Lint & Format`
- `backend / Strict Diff (args & complexity)`
- `backend / Type Check`
- `backend / Test & Coverage`
- `backend / Security`

**Frontend**

- `frontend / Lint`
- `frontend / Lint (changed)`
- `frontend / Type Check`
- `frontend / Test`
- `frontend / Security`

Enable **Require branches to be up to date before merging**.

Mutation jobs are intentionally **excluded** from required checks until baselines stabilize.

## What CI catches vs manual QA

| PR #4-style issue | Enforced by |
|-------------------|-------------|
| Too many function args | Backend strict diff (`PLR0913`) |
| High complexity | Backend strict diff (`C901`), ESLint changed |
| Constants in `page.tsx` | ESLint changed (`max-lines`, import rules) |
| Unused variables | ESLint repo-wide |
| Missing hook deps | ESLint repo-wide (`exhaustive-deps`) |
| Magic strings | Convention + review; no automated rule yet |
| Acceptance criteria vs plan | `/qa-agent` (manual) |
