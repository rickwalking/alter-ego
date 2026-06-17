# Kaizen Signal — sweep-2026-06-16
Mode: sweep | Generated: 2026-06-16 | Signal window: Phase 8 (PR #23, branch `feat/phase-8-legacy-removal`, 17 commits) + accumulated repo signal (Phases 4–8)
Sources: CI workflows, `.agent/reports/*.qa.md` + `*.dev-summary.md`, `git log`, `scripts/ci/gates.sh`, `scripts/ci/check-integrity.sh`, `scripts/agent_tasks/*.py`, suppression grep

> READ-ONLY analysis. No code edited, no tickets created. Phase 4 approval + Phase 5 emission happen in the main session.

## Failure Classes (ranked by frequency × severity)

| # | Class | Freq | Severity | Gate that SHOULD catch it | Status today |
|---|-------|------|----------|---------------------------|--------------|
| 1 | **`"use client"` boundary violations caught ONLY by `next build`** — but no `build` gate exists in CI or `gates.sh` | 1 firsthand (AE-0155) + structural (every future client-feature-in-RSC) | **High** | a new `frontend:build` gate + a `react-server-components/use-client` ESLint rule | **No gate** — build runs nowhere in CI |
| 2 | **`--no-verify` commits skip `npx lint-staged` (prettier) → blocking `frontend:format` gate fails later** | ≥3 (AE-0132, AE-0141, AE-0154) + noted Phase 7 | High | `frontend:format` (exists, but fires late, after the bypass) | Hook bypassable; no defense-in-depth |
| 3 | **`Dev Complete`/`Review` tickets created without the required `.agent/reports/<id>.dev-summary.md`** → `validate_all_tickets.py` fails in batch | 7 tickets at once (this phase) + recurring drift (AE-0003, AE-0074) | Medium-High | `validate_all_tickets.py` (exists, fires late); root cause = no scaffolding upstream | Validator enforces; scaffolding manual |
| 4 | **Build-output dirs not gitignored pollute lint/QA** (`storybook-static/` untracked, broke eslint until AE-0154) | 1 firsthand + class | Medium | a `frontend:integrity` / pre-flight check on untracked build outputs | Now fixed for known outputs; no guard vs *future* build commands |
| 5 | **Net-non-sandboxed external-QA/cursor tooling can mutate repo / detach HEAD; partial-staging + `--no-verify` lost commits** | recurring class (MEMORY: lost-commits incident; Phase 8 external QA) | High (data loss) | external runner hardening (`scripts/lib/external_agent.sh`) | Partially mitigated (codex `--sandbox read-only`, opencode hang recovery); **no HEAD-detach guard, no worktree isolation** |
| 6 | **Copy-pasted `# type: ignore[attr-defined]` on a non-existent imported symbol** — same suppression cloned across 3 files importing from `openai_embeddings` | 3 files, same root | Medium | `backend:type` (mypy) is being silenced by the ignore itself; `backend:integrity` only catches *net-new* | Pre-existing debt; integrity won't flag |

## Detailed evidence per class

### Class 1 — `"use client"` escapes every gate except `next build` (which CI never runs)
- **Firsthand:** `.agent/reports/AE-0155.dev-summary.md:9` — *"build ok (added required `"use client"` to the hook — reachable from a Server Component via the barrel; caught by the production build)"*. typecheck, lint, and 823 tests all passed; only `next build` caught it.
- **The hole:** `scripts/ci/gates.sh` has **no** `gate_frontend_build` (grep for `build`/`gate_frontend_build` → nothing). `.github/workflows/frontend-quality-gates.yml` has jobs for lint, lint-changed, type-check, legacy-guard, legacy-inventory, test, e2e-auth-baseline, security, format-check, schema-drift, mutation-advisory, integrity — **no build job**. So the one check that catches this class runs nowhere in CI.
- **ESLint gap:** `frontend/eslint.config.mjs` has `react-hooks/rules-of-hooks` + `react-hooks/exhaustive-deps` (lines 55–56) but **no** rule flagging hook/browser-API usage in a file missing `"use client"`. The canonical rule is `eslint-plugin-react-server-components` (`react-server-components/use-client: error`, supports `allowedServerHooks`).
- **Barrel amplifier:** the hook was reachable from an RSC *via a module barrel* — so the violation is invisible at the call site.

### Class 2 — `--no-verify` defeats the only format pre-check
- `.husky/pre-commit` = `npx lint-staged`; `frontend/package.json:34-42` lint-staged runs `eslint --fix` + `prettier --write` on `*.{ts,tsx}` / `prettier --write` on `*.{json,md,css}`. `git commit --no-verify` skips all of it.
- **Recurrence:**
  - `.agent/reports/AE-0132.dev-summary.md:12` — *"Earlier `--no-verify` commits (broken local commitlint/husky JS hook) left two files unformatted; ruff-format remediated them here"*.
  - `.agent/reports/AE-0141.dev-summary.md:9` — *"prettier --check (gate_frontend_format) PASS after fixing 5 files left format-drifted by earlier `--no-verify` migration commits"*.
  - `git log`: `a82d4b0 style(phase-8): prettier-format AE-0154 type re-export (QA fix)` — a whole commit spent re-formatting what the hook would have caught.
- **Root issue:** husky hook is *locally* unreliable (broken commitlint JS hook noted twice) → developers habitually pass `--no-verify` → the format gate becomes the first real check, costing a round-trip.
- `frontend:format` (`gates.sh:172` `prettier --check`) is blocking in CI (`format-check` job) — good — but it fires *after* the bypass, not as defense-in-depth at commit time.

### Class 3 — Dev-Complete without dev-summary file
- `scripts/agent_tasks/schema.py` requires the file: `STATUS_DEV_COMPLETE` → `validate_ticket_file()` (lines ~163-168) errors *"Status Dev Complete but no dev summary at <id>.dev-summary.md"*; `STATUS_REVIEW` requires both `.dev-summary.md` AND `.qa.md` (lines ~134-140). Constants `REPORT_DEV_SUFFIX=".dev-summary.md"` (line ~81).
- `scripts/agent_tasks/create_ticket.py` and `move_ticket.py` **do not scaffold or emit** the dev-summary — they only validate existence. So the dev/orchestrator flow can mark Dev Complete (evidence written into the ticket body instead) and only discover the gap when `validate_all_tickets.py` runs (CI job `agent-ticket-hygiene.yml:32`) — and it fails for *all* offending tickets at once (7 this phase).
- **Older drift instances** (validator existed but content wrong): `AE-0074.qa.md:36` (dev-summary claimed 6 tests, 5 exist), `AE-0003.qa.md:54` ("Ticket / Dev-Summary Drift").

### Class 4 — untracked build outputs pollute lint
- `.agent/reports/AE-0154.dev-summary.md:12` — *"Also gitignored `/storybook-static/` (build-storybook output was untracked and polluted lint)"*.
- Current `.gitignore` + `frontend/.gitignore` now cover `.next/`, `out/`, `build/`, `storybook-static/`, `coverage/`, `playwright-report/`, `.stryker-tmp/`, `reports/`, `*.tsbuildinfo`. The two build-producing scripts are `frontend/package.json:7 "build": "next build"` and `:27 "build-storybook": "storybook build"` — both outputs now ignored. **Residual class:** nothing *guards* that a newly-added build command's output is ignored; the next new build target reopens the hole.

### Class 5 — external-QA / git-discipline data-loss hazards
- Hardening present (`scripts/lib/external_agent.sh`): codex `--sandbox read-only --skip-git-repo-check`; opencode pre-kill + stream-health + 1 retry; ANSI strip; per-run timeout. **Gaps:** no HEAD-detach guard and no worktree isolation — external/cursor tooling runs in the main worktree against current HEAD.
- MEMORY `no-git-add-all-with-uncommitted-work.md`: a prior `add -A` + throwaway-branch flow swept uncommitted work into a deleted commit (recovered via dangling commit). Combined with Class 2's `--no-verify` + partial staging, this is one git-discipline class.

### Class 6 — cloned `type: ignore[attr-defined]` on a missing symbol
- 36 total `type: ignore[attr-defined]` in `backend/src`. A specific clone: `feedback_learning.py:14`, `carousel/phase_artifact_runner.py:37`, `carousel/editorial_workflow_service_helpers.py:151` all do `from ...openai_embeddings import (  # type: ignore[attr-defined]`. `openai_embeddings.py` defines class `OpenAIEmbeddingService` with `embed_dense`/`embed_sparse` — the imported name resolved via the ignore is suspect (likely a stale `embed`/factory symbol). Same suppression copy-pasted = a smell mypy would otherwise flag.
- Other suppression clusters (lower individual severity): 11× `noqa: E501` (all in carousel_template `strategies/*` lazy imports), 6× `noqa: ARG001` (all in `malformed_draft_builders.py` test-fixture builders), 11× `type: ignore[arg-type]`, 10× `type: ignore[assignment]`.

## Notes — which classes a NEW gate catches vs. which need doc/process/refactor
- **New gate catches:** Class 1 (`frontend:build` gate + ESLint `use-client` rule), Class 4 (untracked-build-output pre-flight check).
- **Doc/process/automation:** Class 2 (fix husky reliability + add a server-side / gate-time format defense; document `--no-verify` policy), Class 3 (scaffold dev-summary in `create_ticket.py`/`move_ticket.py`), Class 5 (worktree isolation + HEAD-detach guard in the external runner).
- **Refactor (not a rule change):** Class 6 — fix the real import so the ignores can be deleted (a normal bugfix ticket, not a rule). Listed for transparency; ratchet would only be UP if the integrity gate is later extended to flag *cloned* suppressions.
