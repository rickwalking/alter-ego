# Kaizen Report — sweep-2026-06-16
Mode: sweep | Generated: 2026-06-16 | Signal window: Phase 8 (PR #23, 17 commits) + accumulated repo signal

> **INVARIANT:** every proposal below ratchets the bar **UP or HOLD**. Nothing loosens a threshold, adds a suppression, or weakens a gate. See "Rejected (would loosen the bar)" at the end.
> READ-ONLY: no code edited, no tickets created. Phase 4 approval + Phase 5 emission are done by the main session AFTER human approval.

## Failure Classes (ranked)
| # | Class | Freq | Severity | Gate that should catch it | Proposal |
|---|-------|------|----------|---------------------------|----------|
| 1 | `"use client"` caught only by `next build`, which CI never runs | 1+structural | High | new `frontend:build` gate + ESLint `use-client` rule | P1, P2 |
| 2 | `--no-verify` skips prettier → `frontend:format` fails late | ≥3 | High | format defense-in-depth | P3 |
| 3 | Dev-Complete tickets missing `.dev-summary.md` | 7+drift | Med-High | scaffold upstream | P4 |
| 5 | External-QA can detach HEAD / mutate worktree | recurring | High (data loss) | worktree isolation + HEAD guard | P5 |
| 4 | Untracked build outputs pollute lint | 1+class | Medium | untracked-output pre-flight | P6 |
| 6 | Cloned `type: ignore[attr-defined]` on missing symbol | 3 files | Medium | refactor (bugfix, not rule) | Deferred — see notes |

---

## Proposals (ranked; ratchet UP/HOLD)

### P1 — Add a blocking `frontend:build` gate (run `next build` in CI)  [ratchet: UP] [effort: T2]
- **Failure class:** #1. `"use client"` boundary errors (and any other build-only failure: RSC import rules, `next/dynamic` misuse, route-segment config errors) escape lint+typecheck+test and surface only at `next build`, which currently runs **nowhere** in CI or `gates.sh`.
- **5-whys:** Why did AE-0155 ship broken? → a hook using `useState`/`useEffect` lacked `"use client"`. Why not caught? → typecheck/lint/test don't model the RSC/client boundary. Why? → only the Next.js bundler resolves the RSC graph. Why isn't the bundler run? → there is no build gate. Why? → the gate set was assembled pre-App-Router and never added one. **Root cause: the production build is not part of the gate set, so a whole class of bundler-only errors is unguarded.**
- **External evidence:** the App-Router RSC boundary is only fully validated at build time; Vercel's own guidance and the Next.js docs treat `next build` as the integration check. (Belt-and-suspenders with P2's static rule.)
- **Enforcement (systemic):** new gate function `gate_frontend_build` → `cd frontend && npm run build` (i.e. `next build`); register in the frontend GATES map; add a `build` job to `frontend-quality-gates.yml`. Mark **blocking**.
- **Exact files:** `scripts/ci/gates.sh` (add `gate_frontend_build` + GATES entry, place after `typecheck`); `.github/workflows/frontend-quality-gates.yml` (new `build` job mirroring the `type-check` job, `bash scripts/ci/gates.sh frontend:build`); `docs/guides/qa-checkpoints.md` (document the new gate); `frontend/CLAUDE.md` (note build is a gate).
- **Proof it works:** seed a hook file with `useState` and NO `"use client"`, reachable from an RSC via a barrel → `frontend:build` must FAIL; remove the violation → PASS.
- **Signal eliminated:** all build-only failures (Class 1) become PR-blocking instead of discovered during dev. Note cost: `next build` is the slowest gate (~minutes) — run as its own job, not in `--changed-only` fast path.

### P2 — Add ESLint `react-server-components/use-client` rule (fast, static, pre-build)  [ratchet: UP] [effort: T1]
- **Failure class:** #1, the fast-feedback half. P1 catches it in CI; P2 catches it at lint time (and in the `lint:changed` pre-PR path) so devs never reach the build failure.
- **Root cause:** same as P1; addressed statically.
- **External evidence:** `eslint-plugin-react-server-components` exposes `react-server-components/use-client` ("error") which flags client-only features (hooks like `useState`/`useEffect`, browser globals, event handlers) in files lacking `"use client"`, with an `allowedServerHooks` escape for legitimately-shared hooks. ([roginfarrer/eslint-plugin-react-server-components](https://github.com/roginfarrer/eslint-plugin-react-server-components); alternatives: [@naverpay/eslint-plugin-use-client](https://github.com/NaverPayDev/eslint-plugin-use-client), `@serviceup/eslint-plugin-enforce-use-client`.)
- **Enforcement:** add the plugin as a devDependency, register it in `eslint.config.mjs`, set `react-server-components/use-client: "error"`. Because the repo runs `eslint --quiet` (warnings suppressed), it MUST be `error` to gate (consistent with the AE-0147 `no-else-return` precedent).
- **Exact files:** `frontend/package.json` (devDependency); `frontend/eslint.config.mjs` (plugin + rule); `frontend/CLAUDE.md` (the "use client" guidance at line ~75 gains an enforced rule).
- **Proof it works:** add `useState` to a non-`"use client"` module → `eslint` (frontend:lint) FAILS; add the directive → PASS.
- **Signal eliminated:** Class 1 at the cheapest layer; P1 remains the backstop for non-hook build errors. **Sequencing:** land P2 first (cheap), P1 as the catch-all.

### P3 — Make formatting drift impossible to commit, independent of husky  [ratchet: UP] [effort: T1]
- **Failure class:** #2. `--no-verify` (used because the local husky/commitlint hook is flaky) skips `npx lint-staged`, so unformatted code lands and the blocking `frontend:format` CI gate fails late, costing a re-format round-trip (AE-0132/0141/0154).
- **5-whys:** Why does format drift land? → `--no-verify`. Why `--no-verify`? → husky hook is locally broken (commitlint JS hook noted broken twice). Why does that lose formatting? → the *only* pre-CI format pass is in the bypassable hook. **Root cause: format enforcement has a single, bypassable choke point (husky); there is no defense-in-depth and the broken hook trains developers to bypass.**
- **Enforcement (two parts, both ratchet UP):**
  1. **Fix the hook so it stops being bypassed:** repair/replace the broken commitlint step so husky runs reliably (remove the flaky JS hook or pin it); keep `lint-staged` running prettier. This removes the *reason* to use `--no-verify`. Files: `.husky/pre-commit`, `.husky/commit-msg`, `frontend/package.json` (commitlint config/deps).
  2. **Policy + visibility:** document in `frontend/AGENTS.md` + `CLAUDE.md` that `--no-verify` is prohibited for routine commits; require running `npm run format` (or `prettier --write`) before any `--no-verify` use. The authoritative enforcement remains the existing **blocking** `frontend:format` CI gate (HOLD — already correct), now backed by a working hook.
- **Exact files:** `.husky/pre-commit`, `.husky/commit-msg`, `frontend/package.json`; `frontend/AGENTS.md`, `CLAUDE.md` (Git & Commits section).
- **Proof it works:** make a formatting-broken commit without `--no-verify` → hook reformats/blocks; the existing `frontend:format` gate still FAILS on drift if anyone bypasses (seed: commit an unformatted `.tsx` with `--no-verify`, run `gates.sh frontend:format` → FAIL).
- **Signal eliminated:** the recurring "fix N files left format-drifted by earlier --no-verify commits" round-trips. **Note:** this does NOT weaken the gate — it adds an earlier, working layer and documents policy.

### P4 — Scaffold the dev-summary at ticket creation / Dev-Complete transition  [ratchet: HOLD] [effort: T1]
- **Failure class:** #3. `validate_all_tickets.py` (CI: `agent-ticket-hygiene.yml:32`) correctly requires `.agent/reports/<id>.dev-summary.md` for `Dev Complete`/`Review` (`schema.py` ~163-168, ~134-140), but `create_ticket.py`/`move_ticket.py` never scaffold it — so 7 tickets failed at once with evidence written into ticket bodies instead.
- **5-whys:** Why did 7 tickets fail the validator? → no dev-summary files. Why none? → the dev flow wrote evidence into ticket bodies. Why? → nothing prompts/creates the file. Why? → `create_ticket.py`/`move_ticket.py` only *check* existence, don't *emit* a stub. **Root cause: the artifact the validator mandates has no creation path in the tooling — pure friction, not a quality gap.**
- **Enforcement (HOLD — the validator stays exactly as strict; we remove friction so the bar is *met* not lowered):** when `move_ticket.py` transitions a ticket to `Dev Complete`, if `<id>.dev-summary.md` is absent, **create a template stub** (headed `# Dev Summary: <id>` with the required `## Test Evidence` / AC checklist sections) and print a reminder to fill it — OR add an explicit `scaffold_dev_summary.py` helper invoked by the orchestrator. The validator's existence-AND-content check is **unchanged** (do NOT make it pass on an empty stub — keep the `section_has_content("## Test Evidence")` check).
- **Exact files:** `scripts/agent_tasks/move_ticket.py` (scaffold-on-transition) and/or new `scripts/agent_tasks/scaffold_dev_summary.py`; `scripts/agent_tasks/schema.py` (only to expose the template constant if shared — NOT to relax checks); `docs/guides/qa-checkpoints.md` / orchestrator-skill docs.
- **Proof it works:** transition a fresh ticket to Dev Complete with no report → a stub appears AND `validate_all_tickets.py` still FAILS until `## Test Evidence` is filled (proves the gate isn't weakened).
- **Signal eliminated:** batch validator failures from missing report files; keeps the content requirement intact.

### P5 — Isolate external-QA/cursor runs in a git worktree with a HEAD-detach guard  [ratchet: UP] [effort: T2]
- **Failure class:** #5. External/cursor tooling runs in the main worktree against current HEAD; combined with `--no-verify` + partial staging this has caused lost commits (MEMORY incident) and risks HEAD detachment.
- **5-whys:** Why can external QA lose/corrupt work? → it shares the main worktree + HEAD. Why? → the hardened runner sandboxes the *process* (codex read-only) but not the *git state*. Why? → no worktree isolation was added when external QA was introduced. **Root cause: external tooling has process sandboxing but no git-state isolation.**
- **Enforcement:** in `scripts/lib/external_agent.sh` (and `run_external_qa.sh`/`run_external_kaizen.sh`), (a) refuse to launch if `git symbolic-ref -q HEAD` fails (detached HEAD) unless `--allow-detached`; (b) run the external agent inside a dedicated `git worktree add` (auto-removed on exit) so it cannot touch the user's working tree; (c) assert the working tree is clean (or stash-guard) before launch. All additive guards → ratchet UP.
- **Exact files:** `scripts/lib/external_agent.sh` (HEAD guard + worktree create/teardown), `scripts/qa/run_external_qa.sh`, `scripts/kaizen/run_external_kaizen.sh`; `docs/guides/` (external-tooling safety note); MEMORY already documents the incident.
- **Proof it works:** start an external run from a detached HEAD → it ABORTS with a clear error; start with a dirty tree → it isolates in a worktree and the main tree is untouched after the run.
- **Signal eliminated:** lost-commit / detached-HEAD data-loss class.

### P6 — Pre-flight check: untracked build-output directories must be gitignored  [ratchet: UP] [effort: T1]
- **Failure class:** #4. `storybook-static/` was untracked and broke eslint until gitignored (AE-0154). Known outputs are now ignored, but nothing prevents the *next* build command's output from reopening the hole.
- **5-whys:** Why did lint break? → an untracked build dir was linted. Why untracked? → its `.gitignore` entry didn't exist yet. Why no entry? → adding a build script and adding its ignore are separate, unenforced steps. **Root cause: no link between "a build command exists" and "its output is ignored".**
- **Enforcement:** extend `check-integrity.sh` (frontend scope) OR add a tiny `frontend:gitignore-build-outputs` gate that parses `frontend/package.json` scripts for known build tools (`next build`→`.next`,`out`; `storybook build`→`storybook-static`; `vitest --coverage`→`coverage`; stryker→`.stryker-tmp`,`reports`) and asserts each output path is present in `.gitignore`/`frontend/.gitignore`. Additive guard → UP.
- **Exact files:** `scripts/ci/check-integrity.sh` (new check block) or `scripts/ci/gates.sh` (new gate) + `.github/workflows/frontend-quality-gates.yml`; reference list in the script.
- **Proof it works:** add a `"build:foo": "tool build"` script whose output isn't ignored → the check FAILS until `.gitignore` covers it.
- **Signal eliminated:** untracked-build-output lint pollution recurring with each new build target.

---

## Deferred (real signal, but a bugfix not a rule change)
- **Class 6 — cloned `# type: ignore[attr-defined]` on `openai_embeddings` import** across `feedback_learning.py:14`, `phase_artifact_runner.py:37`, `editorial_workflow_service_helpers.py:151`. The fix is to repair the actual import (the imported symbol doesn't exist on `OpenAIEmbeddingService`) and delete the three ignores — a normal backend bugfix ticket, not a systemic rule. A rule-shaped follow-up *would* be UP: extend `check-integrity.sh` to flag *identical* suppression strings appearing in ≥3 files (cloned-ignore detector). Left as a candidate, not a P-proposal, pending the bugfix.

## Rejected (would loosen the bar) — none proposed
The following tempting "fixes" were considered and **rejected by construction** because they loosen the bar:
- ❌ *Make `validate_all_tickets.py` skip the dev-summary requirement (or accept empty stubs)* to stop the batch failures — rejected: removes a check. P4 instead removes friction while keeping the content check (HOLD).
- ❌ *Demote `frontend:format` to advisory / add a `prettier-ignore`* so `--no-verify` drift stops failing CI — rejected: weakens a blocking gate. P3 fixes the upstream hook instead (UP/HOLD).
- ❌ *Add `# type: ignore` / `allowedServerHooks: ["*"]` blanket* to silence Class 1/6 — rejected: suppression. P2 uses a targeted rule; Class 6 gets a real fix.
- ❌ *Skip `next build` because it's slow* — rejected: removing the only check for build-only errors. P1 runs it as an isolated job to bound cost.

## Sequencing recommendation (for the approval gate)
T1 quick wins first: **P2** (use-client lint), **P3** (hook/format), **P4** (dev-summary scaffold), **P6** (gitignore guard). Then T2: **P1** (build gate), **P5** (worktree isolation). Each ticket's AC must include "the gate FAILS on a seeded violation".

## Phase 4 — Human approval (2026-06-16)
Owner approved **ALL 6** proposals, with two scope expansions:
- **P2 broadened** → not just the use-client rule: audit ESLint severities and promote `warn`→`error` for most rules; add code-enforcement rules (best-practice `useEffect`, ban raw `fetch`/effect-data-fetching → force TanStack Query).
- **P1 broadened** → add the build gate AND group CI into **frontend/backend quality-gate categories** (keep `gates.sh` as the QA-phase source of truth). Owner asked if feasible — yes (per-area workflow files and/or `<area> / <gate>` job naming; presentation/orchestration only).

## Phase 5 — Tickets created (Intake, Quality)
- **AE-0166** — Harden ESLint: warnings→errors + use-client / useEffect / TanStack-Query rules (T2, frontend) [P2, broadened]
- **AE-0167** — CI build gate + group quality gates into frontend/backend categories (T2, Cross-cutting) [P1, broadened]
- **AE-0168** — Repair husky pre-commit + `--no-verify` policy (T1, Cross-cutting) [P3]
- **AE-0169** — Auto-scaffold dev-summary on Dev Complete transition (T1, Cross-cutting) [P4]
- **AE-0170** — Worktree isolation + HEAD-detach guard for external runs (T2, Cross-cutting) [P5]
- **AE-0171** — check-integrity pre-flight: build-output dirs must be gitignored (T1, Cross-cutting) [P6]

All 6 are ratchet UP/HOLD; each AC requires the new gate to FAIL on a seeded violation. Status Intake — ready for the planner/architect → developer → qa pipeline when scheduled.
