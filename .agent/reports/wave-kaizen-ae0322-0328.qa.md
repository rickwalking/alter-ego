# Wave QA report — kaizen enforcement wave (AE-0292, AE-0322..AE-0328)

mode: external
Commit: 49b1648c8fb6ab5b15fa2b18ab44fe50d40b4a39
Date: 2026-07-23

## Provenance
Tool: codex (codex-cli 0.139.0, read-only sandbox via scripts/qa/run_external_qa.sh
+ ext_run_guarded worktree isolation). Two initial GLM (opencode-go/glm-5.2)
attempts failed operationally (one mid-stream death, one wedged in the
deps-less worktree) — the engagement-retry hardening for exactly this landed in
this wave (AE-0292). All verdict rounds are codex.

## Rounds
| Round | Verdict | Findings | Fix commit |
|-------|---------|----------|------------|
| 1 (full) | FAIL | 2 critical + 2 warning (F-1 frontend/scripts dirty scope; F-2 generator absorbs NEW-file errors; F-3 missing CAS scenario; F-4 tautological clause tests) | 15441eb5 |
| 2 (full) | FAIL | r1 all RESOLVED; 1 new critical (R2-F1: gate_proof read only the FIRST GATES_JSON line — wave reports pin one per scope) | 0c33ec2b |
| 3 (full) | WARN | ZERO findings; WARN solely for sandbox inability to rerun dependency-backed suites (author-side full gates green, pinned below) + self-referential SHA note | — |
| 4 (confirmation) | PASS | zero findings; integrity re-reproduced (0 blockers) | — |

Finding trajectory 4 -> 1 -> 0 -> 0; no repeated fingerprints; no plateau.

## Gate proof (full runs, final code commit 0c33ec2b)
GATES_JSON: {"pass":16,"fail":0,"skip":4,"results":[{"gate":"backend:format","status":"PASS"},{"gate":"backend:lint","status":"PASS"},{"gate":"backend:lint-diff","status":"PASS"},{"gate":"backend:blanket-ignore","status":"PASS"},{"gate":"backend:strict-diff","status":"PASS"},{"gate":"backend:type","status":"PASS"},{"gate":"backend:imports","status":"PASS"},{"gate":"backend:arch-ratchet","status":"PASS"},{"gate":"backend:docstrings","status":"PASS"},{"gate":"backend:dead-code","status":"PASS"},{"gate":"backend:inline-prompts","status":"PASS"},{"gate":"backend:redis-factory","status":"PASS"},{"gate":"backend:bandit","status":"PASS"},{"gate":"backend:pip-audit","status":"PASS"},{"gate":"backend:integrity","status":"PASS"},{"gate":"backend:test","status":"SKIP"},{"gate":"backend:diff-cover","status":"SKIP"},{"gate":"backend:migrations","status":"SKIP"},{"gate":"backend:schema-drift","status":"SKIP"},{"gate":"backend:mutation","status":"PASS"}]}
GATES_JSON: {"pass":17,"fail":0,"skip":0,"results":[{"gate":"frontend:lint","status":"PASS"},{"gate":"frontend:lint-changed","status":"PASS"},{"gate":"frontend:component-types","status":"PASS"},{"gate":"frontend:duplication","status":"PASS"},{"gate":"frontend:dead-code","status":"PASS"},{"gate":"frontend:typecheck","status":"PASS"},{"gate":"frontend:build","status":"PASS"},{"gate":"frontend:legacy-guard","status":"PASS"},{"gate":"frontend:legacy-inventory","status":"PASS"},{"gate":"frontend:format","status":"PASS"},{"gate":"frontend:security","status":"PASS"},{"gate":"frontend:integrity","status":"PASS"},{"gate":"frontend:test","status":"PASS"},{"gate":"frontend:schema-drift","status":"PASS"},{"gate":"frontend:duplication-tests","status":"PASS"},{"gate":"frontend:dead-files","status":"PASS"},{"gate":"frontend:mutation","status":"PASS"}]}
Backend SKIPs are the 4 Postgres-only gates (test, diff-cover, migrations,
schema-drift) — CI is the authority. check-integrity.sh: backend 0 blockers /
8 ticket-justified warnings; frontend 0 blockers / 1 (AE-0324 apparatus).

## Post-QA fix addendum
All four r1 findings and the r2 finding were FIXED (none accepted/deferred);
each fix ships its own seeded rule-fires test. No findings remain open.
Raw round outputs archived in the session scratchpad; substance recorded here
and in the wave report.
