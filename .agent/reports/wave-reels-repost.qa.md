# Wave QA Report — wave-reels-repost (AE-0626, AE-0627, AE-0628, AE-0629)

**Verdict: PASS** (external, converged over 2 rounds). CI Test & Coverage and Mutation green.

mode: external
Commit: 6419e1048

## Provenance
- Tool: `scripts/qa/run_external_qa.sh` → opencode `plan` agent (read-only), no conversation context.
- Branch `feat/autopilot-reels-repost`, PR #370. Commits `5fa59542c`, `0973045e9`, `15a552090`, `84bf6e408`.
- Round 1 (on `15a552090`): WARN, 0 critical, 1 warning, 2 minor. Saved as `wave-reels-repost.round1.txt`.
- Round 2, confirmation (on `84bf6e408`): PASS. All three findings resolved, no new issues.
- Before round 1, the orchestrator's own Phase 0 found 35 net-new test suppressions (`type: ignore`, `noqa`, a bare `skipif`). CI's Integrity job also failed on them. Fixed in `0973045e9` and `15a552090` with real types, `importlib` and `SecretStr`. The one environment-dependent ffmpeg render test carries `integrity-ok: needs ffmpeg`, which the external reviewer judged legitimate.

## Findings
| ID | Sev | Ticket | Status | Note |
|----|-----|--------|--------|------|
| W1 | warning | AE-0628/0629 | RESOLVED | Boundary mutants. Several were already killed by existing tests (60/59 days, 1/2 drafts, 3.0/90.0 s, one render per tick). Added in `84bf6e408`: an empty future window publishes now; exactly 30 min stays processing and 30 min 1 s times out; unknown metrics sort last. Each mutant was hand-applied and the test failed. |
| S1 | minor | AE-0626 | RESOLVED | `_owned` now fails closed: a Graph answer without `owner` counts as foreign (404). Contract doc updated. |
| S2 | minor | AE-0626/0628 | RESOLVED | Scenarios added: "Every reels and repost route needs the API key" and "Too many calls answer the 429 envelope". The 401 test now also covers the video route and `GET /repost/{id}`. A 7-char Idempotency-Key answers 400. |

## Gate reproduction (orchestrator, single gates on 6419e1048, which is 84bf6e408 merged with main after AE-0630; whole-scope runs are not allowed on this machine)
- All 22 static backend gates PASS, as do `migrations` and `schema-drift` against a throwaway Postgres 16.
- `pip-audit` PASS. It failed earlier on dnspython 2.9.0 and opentelemetry-api 1.45.1, which were pinned on main. AE-0630 (PR #371, merged as e365a2c9e) bumped them, and main was merged into this branch.
- `test`, `diff-cover` and `mutation` were SKIPPED locally; CI decided them. On 86097bef2 (same backend code as 84bf6e408): `backend / Test & Coverage` PASS, `backend / Mutation` PASS at 92.90% (threshold 75%). Mutation never runs locally (AE-0448). Caveat: the new repost and reels modules are not in the mutation paths, so that score does not measure this PR's code.
- The affected suites pass: 1,372 tests (unit autopilot plus the two new integration files).

GATES_JSON: {"pass":24,"fail":0,"skip":3,"results":[{"gate":"backend:format","status":"PASS"},{"gate":"backend:lint","status":"PASS"},{"gate":"backend:lint-diff","status":"PASS"},{"gate":"backend:blanket-ignore","status":"PASS"},{"gate":"backend:strict-diff","status":"PASS"},{"gate":"backend:type","status":"PASS"},{"gate":"backend:imports","status":"PASS"},{"gate":"backend:arch-ratchet","status":"PASS"},{"gate":"backend:docstrings","status":"PASS"},{"gate":"backend:dead-code","status":"PASS"},{"gate":"backend:inline-prompts","status":"PASS"},{"gate":"backend:gherkin-refs","status":"PASS"},{"gate":"backend:comments","status":"PASS"},{"gate":"backend:blog-v1-dead-code","status":"PASS"},{"gate":"backend:redis-factory","status":"PASS"},{"gate":"backend:autopilot-env","status":"PASS"},{"gate":"backend:healthcheck-loopback","status":"PASS"},{"gate":"backend:openapi-fresh","status":"PASS"},{"gate":"backend:bandit","status":"PASS"},{"gate":"backend:pip-audit","status":"PASS"},{"gate":"backend:integrity","status":"PASS"},{"gate":"backend:duplication","status":"PASS"},{"gate":"backend:migrations","status":"PASS"},{"gate":"backend:schema-drift","status":"PASS"},{"gate":"backend:test","status":"SKIP"},{"gate":"backend:diff-cover","status":"SKIP"},{"gate":"backend:mutation","status":"SKIP"}]}
