# Wave QA Report — wave-agent-2a (AE-0242, AE-0243, AE-0244, AE-0245, AE-0247)

**Verdict: PASS** (converged over 2 rounds)

## Provenance
- Tool: `scripts/qa/run_external_qa.sh` → opencode `plan` agent (read-only),
  isolated detached git worktree (AE-0170 guard). External, no conversation context.
- Branch: `chore/agent-restructure-epic-tickets`. Sub-wave commits: `ff220a8a^..ab49fbe1`.
- Rounds:
  - **Round 1** (`/tmp/wave2a-qa-r1.txt`): `INCONCLUSIVE` — gate spine **14/14 PASS**,
    0 critical, 0 warning, **3 minor** (F-1, F-2, F-3). INCONCLUSIVE only because the
    Postgres-dependent gates (`test`, `diff-cover`, `migrations`, `schema-drift`,
    `mutation`) SKIP in the worktree — CI decides those.
  - **Round 2 — confirmation** (`/tmp/wave2a-qa-confirm-out.txt`): `PASS` — all three
    findings RESOLVED, 0 new findings (reviewer re-ran the checker + parity test).

## Findings (all RESOLVED in commit `ab49fbe1`)
| ID | Sev | Ticket | Status | Resolution |
|----|-----|--------|--------|------------|
| F-1 | minor | AE-0243 | RESOLVED | External QA caught a 3rd quality inline prompt (`evaluate_eeat`, "Format as JSON…") not in the arch-plan inventory. Migrated to `quality/v1/eeat.yaml` via `render_prompt` + golden-parity test. `quality_agent.py` now genuinely zero inline prompts. |
| F-2 | minor | AE-0245 | RESOLVED | Map count corrected 21 → 20 files. |
| F-3 | minor | AE-0244 | RESOLVED | Added `"Format as JSON"` to the checker's `PROMPT_MARKERS` (closes the false-negative that let `evaluate_eeat` slip); seeded rule-fires test confirms the class is caught. |

## Gate reproduction (orchestrator, primary tree)
- `gates.sh backend --changed-only` — 0 FAIL (format/lint/lint-diff/strict-diff/type/
  imports/arch-ratchet/docstrings/dead-code/inline-prompts/bandit/pip-audit/integrity PASS).
- `check-integrity.sh backend` — 0 net-new blockers (5 WARN: escaped test noqa + the
  AE-0244/0239 `gates.sh` apparatus edits, justified).
- `pytest tests/unit/agents/ tests/unit/scripts_ci/` — 273 passed.
- Postgres-dependent gates (`test`/`diff-cover`/`migrations`/`schema-drift`/`mutation`)
  → CI is the arbiter.

## Known pre-existing, OUT-OF-SCOPE branch failure (NOT this sub-wave)
`tests/unit/scripts/test_validate_skill_boundary.py::test_skill_boundary_validation_passes`
fails on this branch because commit `04a883b6` ("allow model invocation of delivery
skills") removed `disable-model-invocation` from the **delivery** skills while the
validator still asserts it. Predates the agent-restructure work, on the base
`feat/dev-wave-ae0220-0227` branch (not on `main`), concerns delivery (not runtime)
skills. Flagged for the owner of that policy change; not fixed here (relaxing a
safety-boundary validator is a separate decision).

## Per-ticket
All five PASS. AC's confirmed from code evidence. Test classifications confirmed by QA:
AE-0242/0243 refactor (golden-parity, no `.feature`); AE-0244/0245 CI/tooling+audit
(AE-0244 ships the mandatory rule-fires test); AE-0247 behavior-changing (`.feature`
provided). AE-0243 linkedin no-game DDD deviation accepted.
