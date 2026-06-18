# Kaizen Report — session-2026-06-18
Mode: **session** (AE-0216 smart-handoff loop) | Generated: 2026-06-18 | Signal window: 1 session (AE-0216 build)

> **Scope note (honesty):** this was a **scoped local pass** run inline to test
> `session` mode under a tight context budget — not the full skill pipeline.
> The full `/kaizen-skill session` spawns the Phase-1 research pack + parallel
> Phase-2 subagents + Phase-3.6 external skeptical. Here, claims were verified
> against live code directly (see ✓). Treat proposals as draft pending the
> standard skeptical pass before emission.

Signal source: `.agent/handoff/learnings-log.jsonl` (1 record: AE-0216 session —
3 problems, 4 landmines, 4 decisions).

## Learning Classes (ranked)

| # | Class | From | Severity | Gate/doc that should catch it |
|---|-------|------|----------|-------------------------------|
| L1 | "Merging to main = auto-deploy to prod" is a recurring high-severity landmine, **not stated in root CLAUDE.md** ✓ | landmine + memory `do-droplet-prod-deploy` | High | CLAUDE.md Git section / PR template |
| L2 | Claude Code **hook commands must emit clean stdout**; `uv run` can sync-print and corrupt the hook JSON | problem #3 | High | a harness rule + a clean-stdout test pattern |
| L3 | Context accounting depends on **undocumented transcript `usage` fields**; a CC rename silently zeroes the % | landmine #4 + decision | Med | a canary test on a transcript fixture |
| L4 | External cross-LLM review is **fragile** (model decommissioned, out-of-balance, or hallucinating the subject) | problem #2 | Med | runner fallback chain + an engagement sanity check |

## Proposals (for human review — NOT auto-created)

### K1 — Document "merge to main = prod deploy" in CLAUDE.md  [ratchet: UP] — T1
- **Class L1.** Verified ✓: `grep -in "auto-deploy|merging to main|deploy.yml" CLAUDE.md` → no hits. The fact lives only in `deploy.yml` + a memory file, so every fresh session re-learns it the hard way (it caused the AE-0207 outage).
- **Enforcement:** add a bold warning to the root `CLAUDE.md` **Git & Commits**
  section ("Pushing/merging to `main` triggers `.github/workflows/deploy.yml` →
  full prod redeploy (~12-min blip). Branch + PR; never push `main` directly.")
  + a checkbox in the PR template. Doc/process guard, no code.

### K2 — Codify the Claude Code hook authoring rule + clean-stdout test  [ratchet: UP] — T1/T2
- **Class L2.** Root cause of this session's `uv run` → stdout-corruption risk.
- **Enforcement:** a short rule in `docs/guides/smart-handoff.md` (and/or a
  harness `AGENTS.md`): *hook commands are stdlib-only `python3`, never `uv run`;
  a hook must print valid JSON or nothing to stdout.* Ship a **reusable
  clean-stdout test helper** asserting each hook emits parseable-JSON-or-empty on
  every input (the per-hook tests already do this ad-hoc — generalise it so new
  hooks inherit it). Proves the rule fires.

### K3 — Canary test for the undocumented transcript `usage` contract  [ratchet: UP] — T2
- **Class L3.** Verified ✓: the field literals live in `~/.claude/statusline-pitao.py`
  **and** `scripts/handoff/constants.py:USAGE_FIELDS` — different roots, so dedup
  is impractical; resilience is the right lever (this corrected an initial "DRY
  them" idea — measurement rigor in action).
- **Enforcement:** a test that loads a committed known-good transcript fixture and
  asserts all `USAGE_FIELDS` are present, so a Claude Code rename fails the test
  **loudly** instead of silently zeroing the reminder. Document the fragility
  (already noted in the guide's "Limits" section).

### K4 — Harden the external-review runner  [ratchet: HOLD] — T1
- **Class L4.** This session: `gemini-3-pro-preview` 404 (decommissioned),
  `gemini-2.5-pro` hallucinated (reviewed "aider"), opencode hosted provider out
  of balance — only `opencode-go/glm-5.1` worked.
- **Enforcement:** document a **provider fallback order** in the architect/kaizen
  external-review runbook, and add a cheap **engagement sanity check** ("does the
  review reference the actual subject/filenames?") so a hallucinated review is
  discarded, not trusted. Process/doc; no gate change.

## Rejected (would loosen the bar)
- None. (Notably K3 was *re-scoped*, not dropped, after live-code verification
  showed the cross-root dedup was impractical.)

## Tickets created
- **None** — stopped at the Phase-4 approval gate by design.

## If approved
Emit via `ticket-writer-skill` (K1,K4 = T1; K2 = T1/T2; K3 = T2; Type Quality),
each AC including "the new rule/test FAILS on a seeded violation", then advance
`.agent/handoff/.kaizen-watermark` to this record's `created_at`.
