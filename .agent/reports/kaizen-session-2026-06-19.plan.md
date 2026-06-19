# Kaizen Report — session-2026-06-19
Mode: session | Generated: 2026-06-19 | Signal window: learnings-log records > watermark 2026-06-18T20:33:41-03:00 (2 sessions)

## Method
Read the 2 unreviewed `learnings-log.jsonl` records (planning session + dev/QA wave).
Most listed problems were already `status: fixed` **inside the session**, so the kaizen
value is the **recurring failure classes** that map to systemic enforcement (ratchet UP).
Every candidate fact below was re-verified against live code (per the
`kaizen-measurement-rigor` memory — fitting, since one recurring problem is *agents
asserting unverified facts*).

## Failure Classes (ranked)
| # | Class | Freq | Severity | Gate that should catch it | Status |
|---|-------|------|----------|---------------------------|--------|
| 1 | Anti-hardcoded-prompt checker is a **marker allowlist** — misses any inline prompt lacking 1 of 6 phrases | 1 explicit (`evaluate_eeat`), structural | High | `check_inline_prompts.py` (AE-0244) — the gate itself has the hole | **propose UP** |
| 2 | `external_agent.sh` writes `.wt.log` sidecar adjacent to output → trips AE-0170 worktree guard when output is in tracked `.agent/reports/` | 2 sessions (landmines+problem) | Med-High | check-integrity worktree guard false-trips | **propose HOLD** |
| 3 | `GATES_REQUIRE_ALL=1` leaks into gate-running tests → green-local/red-CI | 2 (AE-0239 + dead-files test) | Med | the test's own env isolation | **propose UP** |
| 4 | Plan subagents assert FALSE current-state facts; only external cold-critic + live-code checks catch them | 2+ (this + `kaizen-measurement-rigor`) | Med | external skeptical (already STANDARD) | **HOLD — codify** |

## Proposals (for approval)

### P1 — Close the anti-hardcoded-prompt checker blind spot  [ratchet: UP] — T2
- **Failure class / root cause:** `check_inline_prompts.py:53` (`_looks_like_prompt`)
  flags a string only if it contains one of **6 hardcoded marker phrases**
  (`PROMPT_MARKERS`, lines 42-49). `evaluate_eeat` was a real inline prompt with
  **none** of them → it sailed past the gate and was only caught by external QA. The
  "fix" appended `"Format as JSON"` to the prompt **and** to the marker list — pure
  whack-a-mole. The **next** inline prompt without any of the 6 phrases is missed
  identically. A gate the developer can dodge by not self-identifying the prompt is gameable.
- **Enforcement (UP):** detect inline prompts **structurally**, independent of marker
  content. Options to spec in the ticket: flag any non-docstring, non-`*_FALLBACK`/`*_TEMPLATE`
  multi-line string literal (≥ N lines) in the scanned dirs that is **passed to an LLM
  call** (`.ainvoke`/`.invoke`, `SystemMessage`/`HumanMessage`, `ChatPromptTemplate.from_*`)
  **or** assigned to a `*prompt*`/`*_PROMPT` name — regardless of markers. Keep the existing
  marker hits as a second OR-branch (no regression).
- **Exact files:** `scripts/check_inline_prompts.py` (detection); a **rule-fires
  regression test** (AE-0180 standard) seeding an inline prompt with **zero** markers and
  asserting non-zero exit; `docs/guides/qa-checkpoints.md` note.
- **Expected signal eliminated:** the `evaluate_eeat`-class (marker-less inline prompt)
  miss; restores the gate as the backstop instead of external QA.

### P2 — Stop the external runner's `.wt.log` from tripping the worktree guard  [ratchet: HOLD] — T1
- **Failure class / root cause:** `scripts/lib/external_agent.sh:119` redirects worktree-add
  stderr to `"$output_file.wt.log"`. The worktree is correctly under `/tmp` (line 118 mktemp),
  but the **sidecar** is written next to `output_file`. When the cold-critic output path is
  inside tracked `.agent/reports/`, the sidecar mutates `git status` (captured line 115) and
  **false-trips the AE-0170 guard** — forcing the documented manual `/tmp` workaround every
  cold-critic run (in both sessions' landmines).
- **Enforcement (HOLD — tooling correctness, loosens nothing):** write the `.wt.log` to a
  `mktemp` path (or `${wt}.log`) outside any tracked dir; clean it up on exit. Removes the
  manual workaround; the guard keeps its full strength.
- **Exact files:** `scripts/lib/external_agent.sh`; a small test/assertion that a runner
  invocation with output under a tracked dir leaves `git status` clean.

### P3 — Make gate-running tests isolate `GATES_REQUIRE_ALL`  [ratchet: UP] — T1
- **Failure class / root cause:** tests that invoke `gates.sh` inherit CI's
  `GATES_REQUIRE_ALL=1`, which flips SKIP→FAIL → green locally, red in CI. Bit twice
  (AE-0239 dead-files SKIP test; the fix was a manual `env.pop` per-test).
- **Enforcement (UP):** an autouse pytest fixture in the gate-tests' `conftest.py` that pops
  `GATES_REQUIRE_ALL` unless a test opts in explicitly — making the class structurally
  impossible instead of relying on each author remembering the `env.pop`.
- **Exact files:** `backend/tests/.../conftest.py` (or the gate-test package conftest); a
  test proving the fixture isolates the var.

### P4 — Codify "live-code-verify current-state claims" for T2/T3 plans  [ratchet: HOLD] — T1
- **Failure class / root cause:** architect/plan subagents asserted 2 false current-state
  facts (skills/runtime "empty"; chat agents "stateless") trusting their own scan. Caught
  only by external cold-critic + manual live-code checks. Recurs (see `kaizen-measurement-rigor`).
- **Enforcement (HOLD — codify existing best practice):** add an explicit "verify every
  current-state assertion against live code; cite file:line" requirement to `architect-skill`
  for T2/T3, and reaffirm the external skeptical pass as **required (not optional)** for T3
  current-state plans. Soft/doc enforcement.
- **Exact files:** `skills/.../architect-skill/SKILL.md`; optional `docs/guides` note.

## Rejected / no-action (would loosen, or already resolved)
- **AE-0237** `create_ticket.py` BOARD-absent crash — **shipped to prod** (record 6, wave 1). Resolved.
- **AE-0253** `validate_skill_boundary` obsolete `disable-model-invocation` — **shipped + seeded tests**. Resolved.
- **linkedin `_TEMPLATE`** can't reach the registry — **working as intended** (forbidden
  application→agents edge, down-only arch ratchet; memory `prompt-registry-ddd-boundary`). No change.
- **PLR0911 per-file-ignore not inherited on harness split** — the system worked (forced a
  real refactor, no suppression). No ticket. (Latent: `app_factory` still carries a PLR0911
  per-file-ignore worth auditing — noted, not ticketed.)
- **Dead Code transient network blip** — single flaky-infra occurrence; AE-0239 tool-preflight
  SKIP already mitigates. No ticket.

## Phase 3.6 — External cold-critic (skeptical) — Verdict: BLOCK
Run: `scripts/kaizen/run_external_kaizen.sh` (opencode), blind packet, output
`.agent/reports/kaizen-session-2026-06-19.skeptical-review.md`. Every finding was
re-verified against live code (advisory, not authoritative). **All findings this
round verified as ACCURATE** — the pass materially improved P1, P2, and P4.

### Decision Log (each finding resolved)
- **P1 / BLOCKER "data-flow infeasible + wouldn't catch evaluate_eeat" — ACCEPTED.**
  Verified: the pre-migration `evaluate_eeat` prompt (now `quality/v1/eeat.yaml`) was
  ~4 lines, **marker-less**, assigned to a generic local `prompt`. It evades a marker
  allowlist, a line-count threshold, **and** a `*_PROMPT`-name check alike. My original
  "passed-to-LLM-call / `*_PROMPT`-name" mechanism would NOT have caught it.
  → **P1 revised** to be goal-oriented, not mechanism-prescriptive (below).
- **P1 / BLOCKER "`*_PROMPT` trigger vs `*_FALLBACK_PROMPT` exemption priority" — ACCEPTED.**
  → ticket AC requires an explicit exemption-priority chain (`docstring > FALLBACK/TEMPLATE
  > detection`) + a negative test asserting `_X_FALLBACK_PROMPT` is NOT flagged.
- **P2 / WARN "output-file leak persists" — ACCEPTED (confirmed in code).**
  `external_agent.sh:147` compares `status_after != status_before` on the **primary** repo;
  the output file written to a tracked path mutates primary status independently of `.wt.log`.
  Moving only the sidecar is a partial fix. → **P2 revised**: stage BOTH output and sidecar
  outside the tracked tree, copy the output to the requested path **only after** the guard
  check passes. Fully closes the class.
- **P2 / WARN "no cleanup trap" — ACCEPTED (minor).** → AC adds a cleanup trap for the staged temp files.
- **P3 / INFO — critic concurs it is sound and low-risk.** No change; conftest placement as scoped.
- **P4 / WARN "self-enforced doc rule is circular; may induce hallucinated cites" — ACCEPTED.**
  The mechanism that actually caught both incidents is the **cross-LLM external skeptical
  pass**, not self-citation. → **P4 revised**: the ratchet is making external skeptical
  **REQUIRED** for T3 current-state plans (change `architect-skill/SKILL.md:32` from
  "skeptical if high-risk"); the self-cite guidance stays as soft, explicitly non-ratcheting
  advice. Also update the tier table + `config.yaml` (critic INFO).

### Revised proposals (post-critic, what the tickets will encode)
- **P1 (T2):** GOAL — the checker must fire on the `evaluate_eeat`-class miss (short,
  marker-less, generically-named inline prompt). Recommended direction: invert to the
  **LLM-call boundary** — every argument to a model invocation (`.ainvoke`/`.invoke`,
  `SystemMessage`/`HumanMessage`, `ChatPromptTemplate.from_*`) must originate from
  `render_prompt()` or a `*_FALLBACK`/`*_TEMPLATE` constant, checked intra-procedurally
  (the dominant pattern), PLUS flag helper functions in the scanned dirs that `return` a
  bare multi-line string literal. AC: a **rule-fires regression test** seeding an
  `evaluate_eeat`-shaped fixture (short, no marker, name `prompt`) MUST fail the gate; the
  explicit exemption-priority chain is tested. Acknowledge no single heuristic is complete;
  the implementer proves the chosen one on the fixture.
- **P2 (T1):** stage output + `.wt.log` to a `mktemp` location, run, guard-check, then copy
  output to the destination; cleanup trap. AC: a test where output is requested under a
  tracked dir leaves `git status` clean and still produces the output.
- **P3 (T1):** unchanged — autouse conftest fixture isolating `GATES_REQUIRE_ALL` + a test.
- **P4 (T1):** make external skeptical REQUIRED for T3 current-state plans
  (`architect-skill/SKILL.md` line 32 + tier table + `config.yaml`); soft file:line-cite
  guidance labeled non-ratcheting.

## Tickets created
- (emitting now — see below)
