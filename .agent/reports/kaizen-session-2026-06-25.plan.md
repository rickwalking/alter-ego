# Kaizen Report — session-2026-06-25

Mode: session | Generated: 2026-06-25 | Signal window: 2026-06-22 → 2026-06-25 (4 learnings records, watermark `2026-06-19T12:18:16Z`)

Source: `.agent/handoff/learnings-log.jsonl` records 8–11 (AE-0263/0266 image+palette epic, AE-0267 palette-catalog epic, AE-0272 responsive-dashboard epic, kaizen→prod session). All gap claims re-verified against live code (3 Explore subagents, file:line evidence).

## Failure Classes (ranked)

| # | Class | Freq | Severity | Gate that should catch it | Status |
|---|-------|------|----------|---------------------------|--------|
| C1 | **Render-invisible CSS/layout bugs** — Tailwind v4 `@theme` tree-shakes vars used only in `[var(--x)]` → empty at build; flex item missing `min-w-0` → page overflow; z-index nested-context trap | 4 bugs (rec 11) + recurring gotcha | **HIGH** — every desktop page broke; caught only post-deploy by user | none (17 gates compile CSS, never render it) | **OPEN — propose P1+P5** |
| C2 | **Cross-layer FE→backend contract gap** — FE sends new value shape (UUID theme) to existing endpoint; backend enum/length cap rejects → 422/500 | 1 go-live blocker (rec 10) + memory `cross-layer-validation-gap` | **HIGH** | per-scope gates never exercise the FE→BE path | **OPEN — propose P5** |
| C3 | **Alembic migration portability drift** — autogenerate emits `postgresql.JSONB/UUID`, `sa.false()` vs sqlite-portable generic types → migrations gate red | 1 CI red (rec 10) + **4 existing committed violations** | MEDIUM | migrations gate detects drift, not the postgres-type root cause | **OPEN — propose P2** |
| C4 | **External-QA default points at out-of-balance route** — `TOOL="${3:-opencode}"`; opencode/glm = "Insufficient balance"; manual switch to codex every time | recs 8,10,11 + prior 2026-06-18 | MEDIUM (friction/lost time) | a preflight balance check (none exists; fails mid-run) | **PARTIALLY ticketed — AE-0219 (Intake, doc-only, under-ratcheted) → propose P3 strengthen** |
| C5 | **External worktree guard hard-resets local commits** — commit during a live external run → AE-0170 guard `git reset --hard` to pre-run HEAD, no lock | 1 lost commit (rec 8) | MEDIUM-HIGH (data loss; recovered via push) | a lock preventing commit-during-run (none) | **OPEN — propose P4** |
| C6 | QA-loop gate-proof gaming | rec 8 | — | move-time gate-proof | **HELD — ticketed AE-0258/0259/0260 on open PR #60; action = merge, no new ticket** |
| C7 | Config SSOT desync (two strategy maps / scattered theme config) | rec 9 | — | drift-guard | **HELD — ticketed AE-0266 (In Development)** |
| C8 | Image-revision feedback ignored | recs 8,9 | — | — | **HELD — ticketed AE-0263 (Intake)** |
| — | Backend script CWD/.env footgun | rec 10 | LOW | — | **DROPPED** — conflicting evidence (Settings has no `extra="forbid"`; `export_openapi.py` is already CWD-agnostic via `__file__`). Not worth a rule. |

## Proposals (for approval)

### P1 — Tailwind `@theme` tree-shake lint gate  [ratchet: UP]  · T2 · frontend
- **Class:** C1. **Root cause:** Tailwind v4 drops `@theme{}` custom vars referenced only inside arbitrary-value utilities (`w-[var(--sidebar-width)]`) — the var resolves EMPTY at build, silently breaking layout. Compiles clean; invisible to all 17 gates.
- **Enforcement:** new `frontend/scripts/check-theme-var-usage.mjs` (mirrors existing `check-responsive-dashboard.mjs` / `check-palette-drift.mjs` pattern) wired into `npm run lint` + `gates.sh frontend`. Flags any `--var` declared in a `@theme{}` block that is referenced ONLY via `[…var(--var)…]` arbitrary values and never as a real Tailwind token. **Rule-fires test** on a seeded violation (AE-0180 mandatory).
- **Immediate value:** audit found **5 live vars already at this risk** (`--shadow-neon-button{,-hover}`, `--shadow-neon-card-hover`, `--shadow-neon-danger`, `--color-neon-cyan-teal-end`, `--color-neon-cyan-border-30`) — the gate flags real existing breakage, not just future.
- **Files:** `frontend/scripts/check-theme-var-usage.mjs` (new), `frontend/scripts/check-theme-var-usage.test.ts` (new, rule-fires), `frontend/package.json` (lint chain), `scripts/ci/gates.sh` (register), `docs/guides/qa-checkpoints.md`.

### P2 — Alembic migration portability gate  [ratchet: UP]  · T1–T2 · backend
- **Class:** C3. **Root cause:** autogenerate emits postgres-specific types; the model is sqlite-portable → CI migrations gate goes red mid-PR.
- **Enforcement:** new grep-based check (a `check-integrity.sh` pattern or small `scripts/ci` gate) flagging `postgresql.JSONB|postgresql.JSON|postgresql.UUID|sa\.false\(|sa\.true\(` inside `backend/alembic/versions/*`. **Rule-fires test** on a seeded violation. The 4 pre-existing violations get an `integrity-ok:` grandfather marker (documented) or a one-line fix — decided at dev time.
- **Files:** `scripts/ci/check-integrity.sh` (or new gate in `gates.sh`), a rule-fires test, `docs/guides/qa-checkpoints.md`.

### P3 — Strengthen AE-0219: fix the actual default + fail-fast preflight  [ratchet: UP]  · T1 · Cross-cutting  · **UPDATE existing ticket, not new**
- **Class:** C4. **Why update, not new:** AE-0219 already exists (Intake, filed by the 2026-06-18 kaizen) but is **doc-only** ("document a fallback order") and was never done — meanwhile the friction recurred in recs 8/10/11. A doc can't fix it because `run_external_qa.sh:21` / `run_external_kaizen.sh:25` hardcode `TOOL="${3:-opencode}"` (the out-of-balance route). Doc-only = under-ratchet.
- **Enforcement (added to AE-0219 ACs):** (a) change the script default to the approved chain head (**codex/gpt-5.5**); (b) add a **preflight reachability/balance probe** in `scripts/lib/external_agent.sh` that surfaces "Insufficient balance / provider unreachable → next in chain" and auto-advances, instead of failing mid-run.
- **Files:** `scripts/qa/run_external_qa.sh`, `scripts/kaizen/run_external_kaizen.sh`, `scripts/lib/external_agent.sh`, the AE-0219 ticket ACs.

### P4 — External-run commit lock  [ratchet: UP]  · T2 · Cross-cutting
- **Class:** C5. **Root cause:** `ext_run_guarded` (`external_agent.sh:143-150`) does `git reset --hard` to pre-run HEAD if HEAD changed during a run, with **no lock** stopping the user from committing meanwhile → a real commit was silently discarded (recovered only because it was pushed).
- **Enforcement:** runner writes a lockfile (e.g. `.git/EXTERNAL_RUN_ACTIVE`) at start / removes on exit; a `pre-commit` hook check refuses to commit while it exists, with a clear message. Converts a silent destructive reset into a friendly block. **Rule-fires test** = commit attempt with lock present is rejected.
- **Files:** `scripts/lib/external_agent.sh`, `.husky/pre-commit` (or a `scripts/ci` helper), a test. *(Could fold into AE-0219 since it's the same runner file — flag at approval.)*

### P5 — Visual + cross-layer verification doc ratchet  [ratchet: UP]  · T1 · docs
- **Classes:** C1 + C2 (the process half — the lint gates above are the mechanical half). **Root cause:** gates compile but never render; per-scope gates never exercise FE→BE.
- **Enforcement:** add to `frontend/AGENTS.md` + `CLAUDE.md` + `docs/guides/qa-checkpoints.md`: (a) shell/layout/responsive tickets MUST include Playwright-MCP verification at **390 + 1440** viewports before Dev Complete; (b) any FE change sending a **new value shape to an existing backend endpoint** MUST ship an integration test that exercises the real contract. Codifies memories `external-qa-catches-drawer-correctness` + `cross-layer-validation-gap` as written rules.
- **Files:** `frontend/AGENTS.md`, `CLAUDE.md`, `docs/guides/qa-checkpoints.md`. *(Process/doc ratchet — no mechanical gate, so lower confidence it'll be honored; pairs with P1.)*

## Rejected (would loosen the bar)
None. Every learning pointed at stronger enforcement, not weaker.

## Held (already ticketed — no new ticket, action noted)
- C6 QA-loop gate-proof → **AE-0258/0259/0260**, open PR #60 (action: merge when ready for prod deploy).
- C7 config SSOT → **AE-0266** (In Development).
- C8 image-revision feedback → **AE-0263** (Intake).
