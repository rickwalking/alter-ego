# Kaizen Improvement Plan — session-2026-07-22 (rev 2, post-cold-critic)

Mode: session | Signal: `.agent/reports/kaizen-session-2026-07-22.signal.md`
Skeptical review: `.agent/reports/kaizen-session-2026-07-22.skeptical-review.md`
(GLM 5.2 cold critic, verdict WARN — every finding verified vs live code and
resolved in the Decision Log below). Nothing below is created/edited until
Phase-4 human approval.

## P1 — Dirty-tree guard in gate-capture.sh  [ratchet: UP] (T1, backend+frontend tooling)
- **Failure class**: FC-1 — diff-based gates false-green on uncommitted/untracked
  work (AE-0301: 2 real ruff violations hid behind "No changed Python files").
- **Root cause**: `lint-diff`/strict-diff/integrity compare committed HEAD vs
  origin/main; untracked files are invisible; gate-capture wraps them with no
  working-tree pre-flight.
- **Enforcement**: `scripts/ci/gate-capture.sh` pre-flight: `git status --porcelain`
  scoped to the gate's source dirs (backend/ for backend, frontend/src for frontend,
  + scripts/). If untracked or modified **source** files exist in scope:
  - default: **exit 2 with a DIRTY-TREE error** naming the files ("diff gates
    cannot see uncommitted work — commit first"),
  - override: `GATE_CAPTURE_ALLOW_DIRTY=1` (for the known multi-session-dirty-tree
    reality) which downgrades to a loud warning **and stamps `"dirty":N` into the
    echoed GATES_JSON line**.
- **Named consumer that blocks (cold-critic BLOCKER-1 resolution)**: extend
  `scripts/agent_tasks/gate_proof.py` (the existing AE-0258 move-time GATES_JSON
  parser, verified live) so `"dirty">0` **BLOCKS the Dev Complete/Review
  transition** unless the dev-summary carries a `DIRTY_WAIVER:` line naming the
  out-of-scope files and why they belong to other sessions. Same
  observability+friction ratchet design the critic previously accepted for
  AE-0258 (CI on the committed tree stays the final authority). The override is
  therefore NOT a silent disable: it converts a false green into a visible,
  waiver-gated state.
- **Files**: `scripts/ci/gate-capture.sh`, `scripts/agent_tasks/gate_proof.py`;
  seeded-violation tests in `backend/tests/unit/scripts_ci/` (untracked seeded
  file → exit 2; ALLOW_DIRTY=1 → dirty count stamped) and in the gate_proof tests
  (dirty>0 without waiver → transition blocked). AE-0180 rule-fires test mandatory.
- **Expected signal eliminated**: the "commit first, then gate-capture" landmine
  stops being tribal knowledge; false-green class closed at the wrapper.

## P2 — Implement AE-0292 + engagement sanity check  [ratchet: UP] (T1, tooling; ticket EXISTS)
- **Failure class**: FC-2 — external runner defaults to unfunded Zen route;
  engagement failures (empty output, refused verification) detected only by humans.
- **Enforcement** (scope-extends existing Intake ticket AE-0292, no new ticket):
  1. `scripts/lib/external_agent.sh`: pin `-m "${EXT_OPENCODE_MODEL:-opencode-go/glm-5.2}"`
     on the `opencode run` invocation. (Cold-critic BLOCKER-2 resolution: the
     funded status of `opencode-go/glm-5.2` is evidenced outside the blind packet —
     successful multi-round runs on 2026-07-01 (5 rounds), 2026-07-02 (9 rounds),
     2026-07-08 and 2026-07-17/18; the env var keeps it configurable; the runner's
     existing opencode→codex→cursor-agent fallback chain remains the availability
     hedge, so no new single point of failure is introduced.)
  2. Post-run sanity: empty/whitespace-only output → retry once with a
     "do NOT use tools — respond with analysis only" preamble (the 2026-07-18 r2
     lesson), then hard-fail with a distinct exit code so the tool-fallback chain
     engages instead of a silent empty verdict.
  3. Runbook notes: stdin `</dev/null`, background + Monitor for 3–8-min runs;
     document the funded-route list next to the env var.
- **Files**: `scripts/lib/external_agent.sh`, `scripts/qa/run_external_qa.sh`,
  seeded test (fake `opencode` shim asserting the `-m` arg + empty-output retry).
- **Action**: promote AE-0292 Intake → Ready with these ACs appended.
- **Expected signal eliminated**: "Insufficient balance" dead runs; silent empty
  verdicts rubber-stamping a wave.

## P3 — Comment/string-safe parsing in check-schema-drift.mjs  [ratchet: UP] (T1, frontend)
- **Failure class**: FC-3 — `// AE-0298` inside a Zod literal reported as
  EXTRA-FRONTEND-FIELD; "fix" was deleting legitimate comments (gate steering style
  via a parser bug).
- **Root cause**: `splitTopLevelFields()` char-walks raw source; no comment or
  string-literal awareness (`//`, `/* */`, and `,`/`{` inside strings all corrupt
  field extraction).
- **Enforcement** (amended per cold-critic WARN-3): replace the hand-rolled
  char-walker with **TypeScript compiler API extraction** (`typescript ^5` is
  already a direct frontend dependency, verified) of the object-literal property
  names — no bespoke comment/string stripping to get subtly wrong. AE-0180
  rule-fires tests: (a) seeded literal WITH inline comments parses to the correct
  field set, (b) seeded genuine drift still FAILS, plus **false-negative guards**:
  template literals, regex literals, strings containing `//`, nested quoted keys.
- **Files**: `frontend/scripts/check-schema-drift.mjs`, its test file; remove the
  now-obsolete landmine from memory/docs after merge.
- **Ratchet note**: UP, conditional on the false-negative test set passing (the
  critic is right that a naive stripper could trade false positives for silent
  false negatives — the compiler-API route + tests is the mitigation).

## P4 — `noUncheckedIndexedAccess` adoption spike  [ratchet: UP] (T2, frontend)
- **Failure class**: FC-4 — unguarded `Record[key]` lookup took down the admin blog
  listing in prod (AE-0295). Instance fixed; class unenforced.
- **Enforcement** (amended per cold-critic WARN-4 — pre-committed decision rule,
  no open-ended spike): run `tsc` with `noUncheckedIndexedAccess: true` and count
  errors. **Decision rule fixed in the ticket AC**: ≤40 errors → fix and enable
  the flag in the SAME ticket; >40 → the SAME ticket still lands an enforceable
  artifact: flag ON in a dedicated `tsconfig.strict-index.json` typecheck gate
  over an allowlisted (initially small) directory set + a down-only error-count
  baseline for the rest, wired into `gates.sh frontend`. The ticket is NOT
  closable on a report alone — its AC requires a gate that fails on a seeded
  unguarded `Record[key]` access (AE-0180).
- **Files**: `frontend/tsconfig.json` (+ fallout fixes or a ratchet script).
- **Expected signal eliminated**: the whole "missing-key destructure → prod
  TypeError" class becomes a compile error.

## P5 — One-command contract regen: `make regen-contracts`  [ratchet: HOLD] (T1, backend)
- **Failure class**: FC-5 — every API-contract change rediscovers 4 regen steps via
  4 red gates (+ the export_openapi.py CWD/.env landmine).
- **Enforcement**: `scripts/dev/regen_contracts.sh` (cd's into backend/ itself,
  killing the .env landmine) running: `export_openapi.py`,
  `REGEN_ROUTE_SNAPSHOT=1 pytest <route-snapshot test>`, publishing + editorial
  snapshot tests with `--snapshot-update`. Makefile target `regen-contracts`.
  Documented in `docs/guides/` (linked from backend CLAUDE.md's commands section).
  **Amended per cold-critic WARN-5 (partial-regen visibility)**: `set -euo
  pipefail` — abort on the FIRST failing step with a clear "regen INCOMPLETE,
  artifacts may be inconsistent" banner; final step re-runs the four snapshot/
  contract tests **read-only** and the script only exits 0 when all four verify
  green, so a half-updated state cannot look done. (`--snapshot-update` writes are
  already how these artifacts are maintained today; the pinned CI gates remain
  the commit-time enforcers.)
- **Ratchet note**: HOLD — no gate loosened; the pinned gates remain the enforcers,
  this removes the friction that tempts people to game them.

## P6 — Codify the external-review convergence criterion  [ratchet: HOLD] (T1, docs/skills)
- **Failure class**: FC-6 — the ≥3-findings cold-critic prompt makes literal-zero
  unreachable; two sessions independently re-derived "3 consecutive zero-blocker
  rounds = converged".
- **Enforcement**: document in `skills/delivery/architect-skill` skeptical-mode
  reference + kaizen-skill external runbook: convergence = **3 consecutive rounds
  with zero BLOCKERs** (severity trajectory, not verdict text); never edit the
  ≥3-findings mandate downward (that would be the down-ratchet). Add the prettier
  non-idempotence landmine (wrapped inline code spans in .md) to the same runbook
  page as a one-liner. **Amended per cold-critic WARN-6**: documented as the
  **default** stop rule, not absolute — overridable in either direction with a
  recorded justification in the review record; include the calibration caveat
  that BLOCKER/WARN boundary drift across reviewer models is a known noise
  source (n=2 sessions is the current empirical basis; revisit if a converged
  wave later ships a blocker-class defect).
- **Ratchet note**: HOLD — stops both infinite polishing and premature stops.

## Supplemental candidates (outside the log window; latest-session flags)
Per cold-critic INFO-7 (a known clobbering prod bug must reach a ticket DECISION
this cycle, not drift as a candidate), both are presented at the Phase-4 gate as
first-class approve/reject items rather than "undecided" carry-overs:
- **S1 — PATCH /slides checkpoint-staleness clobber** → bugfix ticket: merge against
  the live projection (or re-run repair post-merge server-side). [ratchet: UP]
- **S2 — NSFW/non-humanoid guard clause in image prompts** → ticket: bake a safety
  clause into `_compose_scene`/style wrap so `custom_visual_details` cannot steer
  into moderation-risky humanoid output. [ratchet: UP]

## Cold-critic Decision Log (all findings verified vs live code before resolution)
| Finding | Disposition |
|---------|-------------|
| BLOCKER-1 dirty-override is a silent down-ratchet | ACCEPTED → P1 amended: `gate_proof.py` (verified live consumer) blocks transition on `dirty>0` without a `DIRTY_WAIVER:` line |
| BLOCKER-2 model pin evidence / SPOF | RESOLVED with out-of-packet evidence: funded route proven across 4 sessions of successful runs; env-var override + existing codex/cursor fallback chain negate the SPOF claim |
| WARN-3 hand-rolled parser may add false negatives | ACCEPTED → P3 amended: TS compiler API (dep verified present) + false-negative test set |
| WARN-4 spike lacks threshold/forcing function | ACCEPTED → P4 amended: pre-committed ≤40/>40 rule; ticket must land an enforceable gate either way |
| WARN-5 partial-regen invisibility | ACCEPTED → P5 amended: fail-fast + read-only verify pass before exit 0 |
| WARN-6 n=2 convergence rule canonized | ACCEPTED → P6 amended: default-not-absolute + calibration caveat |
| INFO-7 S1 unowned drift | ACCEPTED → S1/S2 promoted to first-class Phase-4 decisions |

## Rejected (would loosen the bar)
- **Codifying the R16 "fallback evidence" path** (fast `--changed-only` subset +
  pointer to the last full green when background runs get killed) as sanctioned
  Dev-Complete evidence — rejected: it would down-ratchet AE-0259's full-run
  requirement. The killed-runs root cause (host reaping) stays an open observation.
- **Relaxing the ≥3-findings cold-critic mandate** so reviews can return
  literal-zero — rejected: the mandate is anti-rubber-stamp by design; the fix is
  documenting the trajectory-based stop rule (P6).

## Suggested emission order
P2 (recurred twice, ticket exists) → P1 (highest-severity open hole) → P3 → P5 →
P6 → P4 (spike). S1/S2 on user decision.

---

# Addendum (second kaizen pass, same day — consolidation from the 2026-07-17/18 incident-arc sessions)

A parallel session's independent Phase-0 found four classes the first pass
missed — BECAUSE those sessions wrote `HANDOFF-latest.md` directly and never
appended learnings-log records (see P10). Signals verified live 2026-07-22.

## P7 — Repo-wide `from None` observability rule  [ratchet: UP] (T2, backend) — rev 2 post-cold-critic
- **Failure class**: exception chains deliberately suppressed (`raise ... from
  None`) with no logging — 15 sites in `api/routes` alone; one turned the
  2026-07-17 prod incident into an opaque 400 that cost a full forensic session
  (AE-0318 instrumented that one site; the rest remain).
- **Cold critic (addendum-review.md): FAIL on the v1 routes-scoped
  `raise HTTPException` heuristic** — accepted: routes-only scope targets where
  incidents surface, not originate; the trigger shape overlapped legitimate
  translation handlers; "any logger call" enforces syntax, not evidence.
- **Rev 2 (per critic I1)**: AST checker on **`from None` specifically,
  repo-wide** (`src/rag_backend/**`): every `raise ... from None` inside an
  `except` handler requires a `logger.<level>(...)` call in the same handler
  (or a counted `# swallow-ok: <reason>` marker surfaced by check-integrity).
  Down-only baseline for the existing sites. AE-0180 rule-fires test both ways
  + regression run over the real tree recorded in the ticket.
- **Residual accepted**: a token log line satisfies the letter — the AE-0318
  precedent (structured event + error field) is the documented norm; the gate
  makes silence impossible, review makes the log meaningful.

## P8 — Mutation-run integrity diagnosability  [ratchet: UP] (T1, tooling)
- **Failure class**: corrupted mutmut runs are indistinguishable from bad tests —
  3 incidents on 2026-07-17/18 (venv touched mid-run → all-zero stats; flaky
  sandbox baseline → 0.0%; SIGXCPU worker deaths → bogus survivor lists that
  nearly drove wrong "fixes") + 3 externally-killed runs on 2026-07-08.
- **Enforcement**: `scripts/ci/mutation-score-gate.sh`: (a) `denominator == 0`
  while `total > 0` → distinct exit + message "baseline failed or run corrupted
  — rm -rf mutants and rerun; do NOT run uv sync/lock during mutation" (today it
  prints a plain 0.0% FAIL); (b) count `worker exit code -` lines in the run
  output — nonzero → stamp "stats unreliable (N dead workers)" into the output
  and the gate summary; (c) the don't-touch-the-venv rule added to the
  gate-run-loop discipline section in CLAUDE.md. Seeded test: a stats JSON with
  killed=0/total>0 → the distinct corrupted-run exit fires.

## P9 — Two flake/gap bugfix tickets from live prod evidence  [ratchet: UP] (T1 each, backend)
- **P9a — AE-0296 delete-guard CI flake**: `test_delete_linked_carousel_origin_
  is_blocked` failed 204-vs-409 on PR #84's backend-gate, passed untouched on
  rerun (Postgres commit-visibility between the test's direct DB write and the
  request session is the suspect). Ticket: make it deterministic (explicit
  commit/refresh or event-driven wait); rerun rituals normalize red CI.
- **P9b — AE-0312 policy-stamping gap**: prod project f9e3e199 (created
  2026-07-17, post-#83 deploy) outlined with `hero_lower_third_v1` — create-time
  v2 stamping apparently didn't fire on the sources-first creation path.
  Investigation + fix ticket; every affected project renders with v1 casing
  rules until repaired at a gate.

## P10 — Handoff/learnings-log coupling rule  [ratchet: UP] (T1, docs/process)
- **Failure class**: sessions that write `.agent/handoff/HANDOFF-latest.md`
  directly (2 sessions, 07-17/18) skip the learnings-log append — kaizen session
  mode goes blind to exactly the busiest sessions. Proven by this very cycle:
  the first pass today missed P7–P9's signal for this reason.
- **Enforcement**: rule in the handoff workflow docs + CLAUDE.md agentic
  section: a direct HANDOFF write MUST append a matching learnings-log record;
  kaizen Phase 0 gains a staleness check (HANDOFF-latest.md mtime newer than the
  log's last record → warn "unlogged session learnings — mine the handoff file
  too", which is what saved this cycle).

## Addendum cold-critic log
| Finding | Disposition |
|---|---|
| P7 v1 FAIL (scope/trigger/evidence critique) | ACCEPTED in full → P7 rev 2: `from None`-targeted, repo-wide, baseline-ratcheted |
| P8–P10 | T1 trivia tier — skeptical round skipped per skill policy; facts grep/incident-verified live |
