# Phase 8 Class B — QA Wave Report

Branch: `chore/phase-8-class-b` | Tickets: AE-0166..0171 | Date: 2026-06-17

## Method

Four parallel adversarial QA reviewers over the full wave diff (`origin/main..HEAD`):
security, code-quality, acceptance-criteria, and integrity/anti-gaming. Findings
triaged, fixed, and each fix re-verified empirically.

## Gate Status (post-fix)

| Suite | Result |
|-------|--------|
| Frontend gates (`gates.sh frontend`) | **16/16 PASS** (lint, lint-changed, component-types, duplication, dead-code, typecheck, build, legacy×2, format, security, integrity, test, schema-drift, dup-tests, mutation) |
| Backend agent_tasks tests | 11 passed, 1 skipped |
| mypy (changed scripts) | clean |
| `validate_all_tickets.py` | 177 OK |
| Backend gates | 13 PASS / 3 SKIP / 1 FAIL = `pip-audit` (pre-existing langchain GHSA-gr75-jv2w-4656, 1.2.15→1.3.9; wave touched no deps — out of scope, own ticket) |

## Findings & Resolutions

| # | Sev | Dimension | Finding | Resolution |
|---|-----|-----------|---------|------------|
| H1 | BLOCKER | code-quality, integrity | Scoped `no-restricted-syntax` warn block (`src/modules`+`components`) silently OVERRODE the global `fetch`-in-`useEffect` **error** — ESLint flat config replaces, not merges, same-key rules. The flagship rule was unenforced in the main app dirs. | Removed the colliding scoped raw-fetch block. `useEffect`-`fetch` is now a real error everywhere; locked by `eslint-fetch-rule.test.ts` (lints a probe under `src/modules`). Verified: probe → 1 error, `--quiet` exit 1. |
| H2 | MEDIUM | code-quality, integrity | `eslint.config.mjs` comment claimed warn rules were diff-enforced via `--max-warnings=0`, but `eslint-changed.mjs` ran `--quiet` (warnings suppressed). False enforcement claim. | `--max-warnings=0` would force unrelated refactors of pre-existing warnings in any touched file (verified: 15 pre-existing warnings in files I added one line to). Instead made `lint:changed` SURFACE warnings (dropped `--quiet`) as a paydown nudge; corrected the comment to "advisory, not gating". |
| M1 | MEDIUM | code-quality | AE-0169 scaffold + `schema.py` existence-only check → an unfilled placeholder dev-summary could satisfy the Dev Complete/Review gate. | Added `DEV_SUMMARY_SCAFFOLD_MARKER` sentinel check (`_dev_report_errors`); rejects an unreplaced scaffold. +2 tests. Refactor reduced `can_transition` complexity (C901 18→17 vs main). |
| M2/L1 | LOW | code-quality, security | `check-use-client.mjs` read only first 3 lines (false-positive on a directive after a license/JSDoc block) and matched hook names inside comments. | Strip block+line comments before scanning; recognize a directive preceded by comments. +2 tests. Real tree still 171 files OK. |
| L2 | LOW | security, code-quality | `ext_run_guarded` checked only HEAD/branch, not primary working-tree mutation — header overclaimed. | Added `git status --porcelain` tripwire (reports, doesn't auto-revert legit work); guard self-check gains case C; header made precise. |
| — | NIT | acceptance | `.husky/commit-msg` comment said config lived at repo root (moved to `frontend/`). | Comment corrected. |

## Confirmed Sound (no action)

- AE-0170 worktree isolation + rogue-detach detect/restore (rc 4) — rigorous.
- AE-0171 build-output pre-flight (`git check-ignore` catches tracked artifacts), coverage untrack.
- AE-0168 husky env-unset + absolute msg-path resolution + graceful skip.
- AE-0167 build gate registration + blocking CI job + `--changed-only` skip (legit).
- No blanket disables / threshold drops / suppressions anywhere; severities ratchet UP only.

## Verdict

**PASS** after fix loop. The QA wave caught a genuine gating-integrity blocker (H1) that
would have shipped a non-functional flagship lint rule; it and all mediums are resolved,
tested, and green. Dogfooded: QA-fix commit `ecbc8b3` passed husky pre-commit + commitlint
with no `--no-verify`.

## Deferred / Follow-up (kaizen candidates)

- pip-audit: bump langchain 1.2.15 → 1.3.9 (GHSA-gr75-jv2w-4656) — own dependency ticket.
- Gherkin-first: tooling/infra tickets shipped behavioral tests but no `.feature` files;
  decide whether the mandate applies to infra tickets or only product code.
- Broad raw-`fetch` steering (dropped in H1) — if wanted, implement as a ratchet script
  (like feature-boundaries), not a colliding `no-restricted-syntax`.
