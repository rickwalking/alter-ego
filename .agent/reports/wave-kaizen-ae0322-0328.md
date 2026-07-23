# Wave report — kaizen session-2026-07-22 enforcement wave (AE-0292, AE-0322..AE-0328)

Commit: d5e622e51dcafafc36ce0b73b51c9091c4fbf989
Branch: feat/kaizen-wave-ae0322-0328 (base origin/main 64889be6)
Generated: 2026-07-23

## Tickets
AE-0292 (model pin + engagement retry), AE-0322 (dirty-tree guard),
AE-0323 (schema-drift TS parser), AE-0324 (strict-index gate + baseline),
AE-0325 (regen-contracts), AE-0326 (convergence docs),
AE-0327 (slide-edit re-repair), AE-0328 (image prompt safety clause).
Follow-up emitted: AE-0329 (strict-index full adoption).

## Gate reproduction (full runs, scripts/ci/gate-capture.sh, this commit)

Backend (16 PASS / 0 FAIL / 4 SKIP — Postgres-only: test, diff-cover,
migrations, schema-drift; no local Postgres, CI runs them):
GATES_JSON: {"pass":16,"fail":0,"skip":4,"results":[{"gate":"backend:format","status":"PASS"},{"gate":"backend:lint","status":"PASS"},{"gate":"backend:lint-diff","status":"PASS"},{"gate":"backend:blanket-ignore","status":"PASS"},{"gate":"backend:strict-diff","status":"PASS"},{"gate":"backend:type","status":"PASS"},{"gate":"backend:imports","status":"PASS"},{"gate":"backend:arch-ratchet","status":"PASS"},{"gate":"backend:docstrings","status":"PASS"},{"gate":"backend:dead-code","status":"PASS"},{"gate":"backend:inline-prompts","status":"PASS"},{"gate":"backend:redis-factory","status":"PASS"},{"gate":"backend:bandit","status":"PASS"},{"gate":"backend:pip-audit","status":"PASS"},{"gate":"backend:integrity","status":"PASS"},{"gate":"backend:test","status":"SKIP"},{"gate":"backend:diff-cover","status":"SKIP"},{"gate":"backend:migrations","status":"SKIP"},{"gate":"backend:schema-drift","status":"SKIP"},{"gate":"backend:mutation","status":"PASS"}]}

Frontend (17 PASS / 0 FAIL / 0 SKIP):
GATES_JSON: {"pass":17,"fail":0,"skip":0,"results":[{"gate":"frontend:lint","status":"PASS"},{"gate":"frontend:lint-changed","status":"PASS"},{"gate":"frontend:component-types","status":"PASS"},{"gate":"frontend:duplication","status":"PASS"},{"gate":"frontend:dead-code","status":"PASS"},{"gate":"frontend:typecheck","status":"PASS"},{"gate":"frontend:build","status":"PASS"},{"gate":"frontend:legacy-guard","status":"PASS"},{"gate":"frontend:legacy-inventory","status":"PASS"},{"gate":"frontend:format","status":"PASS"},{"gate":"frontend:security","status":"PASS"},{"gate":"frontend:integrity","status":"PASS"},{"gate":"frontend:test","status":"PASS"},{"gate":"frontend:schema-drift","status":"PASS"},{"gate":"frontend:duplication-tests","status":"PASS"},{"gate":"frontend:dead-files","status":"PASS"},{"gate":"frontend:mutation","status":"PASS"}]}

Note: the backend capture ran at commit 47dd9e5-era HEAD (pyasn1 bump) and the
frontend deps commit (d5e622e5) landed during it; that commit touches only
frontend/package*.json, which no backend gate reads. Frontend capture ran on
the final HEAD.

## Integrity (scripts/ci/check-integrity.sh)
backend: PASS, 0 blockers, 8 warnings (ticket-justified integrity-ok subprocess
markers in new seeded-violation tests + the gate-capture apparatus edit that IS
AE-0322's deliverable). frontend: PASS, 0 blockers, 1 warning
(tsconfig.strict-index.json apparatus edit = AE-0324's deliverable).

## Gate deltas made during the wave (not gaming; recorded)
- backend:pip-audit red on NEW upstream pyasn1 CVEs -> floored pyasn1>=0.6.4
  (fix version), re-locked; gate green.
- frontend:security red on brace-expansion HIGH -> npm audit fix; remaining
  sharp<0.35.0 HIGH -> override sharp ^0.35.3; gate green at --audit-level=high.
- frontend:test one-off failures in 3 subprocess-spawning checker tests during
  a CPU-contended parallel run; all pass in isolation and in the final
  uncontended full run (17/17 gates).
