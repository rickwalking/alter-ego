# Kaizen Signal Report — session-2026-07-22

Mode: session | Generated: 2026-07-22 | Signal window: learnings-log.jsonl records
newer than watermark `2026-06-26T03:20:00Z` → 4 records:

| # | created_at | mission |
|---|-----------|---------|
| R13 | 2026-07-01T19:52Z | Blog/carousel prod-fix planning (AE-0295..0299 + ADR-0013) |
| R14 | 2026-07-01T20:11Z | Blog/carousel dev wave (PR #80) |
| R15 | 2026-07-02T02:11Z | Prod security audit → AE-0300..0307 |
| R16 | 2026-07-08T18:57Z | Security dev wave (PR #81 merged, Redis auth live) |

## Failure Classes (ranked by frequency × severity × still-open)

### FC-1 — Diff-based gates return false greens on uncommitted/untracked work
- **Freq/Sev**: 2 direct incidents + 1 near-miss / HIGH (a false green is the exact
  failure class the whole AE-0258/0259 apparatus exists to kill)
- **Evidence**: R16 — AE-0301 gate-capture said "No changed Python files" while the
  commit-to-be added a `.py` file; external QA then caught 2 real ruff violations
  hiding behind the green. Earlier session landmine (2026-06-24): "Integrity scan AND
  strict-diff gate read COMMITTED HEAD … commit fixes before trusting a PASS."
- **Gate that should catch it**: `scripts/ci/gate-capture.sh` — verified 2026-07-22:
  it has NO working-tree cleanliness check; diff-based gates (`lint-diff`,
  strict-diff, integrity) silently no-op on untracked files.
- **Status**: OPEN. Currently only a memory/landmine ("commit first"), i.e. tribal
  knowledge, exactly what kaizen exists to convert into enforcement.

### FC-2 — External-agent runner defaults to an unfunded route; engagement failures undetected
- **Freq/Sev**: 3+ incidents / MEDIUM (blocks or silently degrades the external QA
  spine that AE-0260 made the default)
- **Evidence**: R16 — `run_external_qa.sh` died "Insufficient balance" (opencode plan
  agent defaults to Zen `glm-5.2`, unfunded); workaround = hand-invoke
  `opencode run -m opencode-go/glm-5.2`. Also: R16 — external QA round refused to
  run read-only verification (plan-mode caution) until the prompt explicitly
  authorized it; 2026-07-18 wave — GLM went agentic and returned EMPTY, needing a
  rerun with "do NOT use tools" prepended.
- **Gate that should catch it**: none — `scripts/lib/external_agent.sh:50` verified
  2026-07-22: `opencode run --agent plan` with no `-m` pin.
- **Status**: OPEN — ticket **AE-0292 already exists (Intake, T1)** but is
  unimplemented; incidents recurred twice since it was filed.

### FC-3 — `check-schema-drift.mjs` naive Zod parsing → false positives steer code style
- **Freq/Sev**: 1 incident + 1 permanent landmine / MEDIUM (a gate that lies erodes
  trust in all gates; the "fix" was deleting legitimate comments)
- **Evidence**: R14 — field `// AE-0298` reported as EXTRA-FRONTEND-FIELD; solution
  was to strip inline comments from `carousel.ts` object literals. Promoted to a
  standing landmine + memory note instead of a parser fix.
- **Gate that should catch it**: the checker itself. Verified 2026-07-22:
  `splitTopLevelFields()` char-walks the literal body with no comment/string
  stripping — any `//` or `/* */` inside a mapped literal corrupts field extraction.
- **Status**: OPEN.

### FC-4 — Unguarded `Record[key]` indexed access crashes prod UI
- **Freq/Sev**: 1 prod incident (whole admin blog listing down) / HIGH severity,
  instance fixed, CLASS unenforced
- **Evidence**: R13 — `badge.tsx` destructured `BLOG_POST_BADGE_COLORS[color]` with
  no fallback; workflow statuses aren't keys → `TypeError` on every non-featured
  card. Fixed as AE-0295 (typed map + fallback), but nothing prevents the next one.
- **Gate that should catch it**: TypeScript `noUncheckedIndexedAccess` — verified
  2026-07-22: NOT set in any frontend tsconfig.
- **Status**: OPEN (class-level).

### FC-5 — Pinned-contract regeneration is 4 separate tribal-knowledge steps
- **Freq/Sev**: every API-contract change (R14 hit all 4: openapi.json, route
  snapshot, publishing snapshots, + .env-CWD landmine on export_openapi.py) / LOW-MED
  (cost = repeated red gates + rediscovery, not a correctness hole)
- **Evidence**: R14 problems 3–4 + landmine "API contract changes require
  regenerating 3 pinned artifacts"; memory `backend-pinned-artifacts-and-ratchets`
  says 4 (adds editorial workflow snapshot). Verified 2026-07-22: no Makefile target
  or script bundles them; recipe lives only in agent memory, not the repo.
- **Status**: OPEN.

### FC-6 — External-review convergence criterion is undocumented
- **Freq/Sev**: 2 sessions independently re-derived it / LOW (wasted rounds, risk of
  either infinite polishing or premature stop)
- **Evidence**: R15 — cold-critic prompt MANDATES ≥3 findings/round, so a literal
  zero-findings verdict is structurally unreachable; convergence had to be tracked
  by BLOCKER trajectory, stopping at 3 consecutive zero-blocker rounds (R7–R9).
  Same criterion re-used ad hoc in the AE-0295..0299 loop (5 rounds). Verified
  2026-07-22: not documented in kaizen-skill or architect-skill references.
- **Status**: OPEN.

## Noted, no proposal
- R16 prettier non-idempotence on wrapped inline code spans in `.md` — rare,
  self-evident once hit, already a landmine; a doc line can ride along with P5's doc
  work if desired.
- R14 GLM R2 "intermittent combined-run failures" — could not reproduce (6 targeted
  + 2 full runs green); watch CI, no action.
- R16 background gate runs killed externally 3× — root cause unknown (host-level);
  no enforceable change identified.

## Supplemental (latest session 2026-07-22, NOT in the log window — user already aware)
- PATCH `/carousels/{id}/slides` merges from the parked CHECKPOINT copy (staler than
  the projection) and rewrites ALL slides — clobbered repair fixes; recovery is
  re-running POST /repair. Bugfix-ticket candidate.
- No NSFW/non-humanoid guard clause in image prompts; `custom_visual_details`
  ("Ghost in the Shell…") steered generation into moderation-risky output.
  Ticket candidate the user explicitly flagged as undecided.
