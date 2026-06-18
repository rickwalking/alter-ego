# AE-0216 — Smart session handoff (/handoff skill + SessionStart injection)

Status: Dev Complete
Tier: T2
Priority: Medium
Type: Tooling
Area: Agent Workflow
Owner: Agent
Agent Lane: architect → developer → qa
Branch: main (uncommitted, pending user review)
Kanban Card: AE-0216
Created: 2026-06-18
Updated: 2026-06-18

## Goal

Let a long Claude Code session continue in a FRESH session without losing its
accumulated learnings — a higher-fidelity alternative to repeated `/compact`.

## Problem

`/compact` keeps the same session and is lossy-on-lossy: decision rationale and
early constraints disappear across cycles. The existing durable memory
(`memory/`, `.agent/`, `CLAUDE.md`) covers cross-session facts but NOT a single
session's in-flight conversational state ("why we did what we did"). That state
is what is lost when context fills.

## Scope

- A model-driven `/handoff` skill that writes a curated handoff (narrative +
  structured JSON) to `.agent/handoff/`.
- A SessionStart hook that re-injects the latest handoff into a fresh/resumed/
  cleared session (skips compaction; dedupes per content-hash + session).
- An optional, non-blocking Stop hook that nudges to checkpoint at ≥70% window.
- Wiring (`~/.claude/settings.json`, skill symlink) + guide doc + tests.

## Non-Goals

- Auto-triggering the handoff (Stop-hook "block" forces continuation, not a
  pause — the external feasibility review proved the auto-trigger design unsound).
- Auto-spawning a seeded new session (no documented CLI flag; the human running
  `/clear` or a new session is the one true seam).
- Replacing the `memory/` or `.agent/` systems (complementary, not a substitute).

## Classification (AE-0153 no-`.feature` path)

- **Tooling / harness** change, not app behavior. **No public/user-visible
  application behavior change** (no API, workflow, or business-rule change in the
  RAG app). New behavior is confined to the developer harness (a slash command +
  Claude Code hooks).
- **Unit tests substitute for `.feature`**: 23 stdlib pytest cases in
  `scripts/handoff/tests/` cover the behavioral edges, including the
  failure/edge "seeded-violation"-equivalent cases (malformed stdin → silent;
  no-handoff → silent; dedupe; skip-on-compact; new-handoff reset; truncation).
- **Affected gates**: none of the existing CI scopes (backend/frontend) cover
  repo-root `scripts/`; tests are run manually via the backend uv/pytest env.
- **QA sign-off on classification**: PENDING (deferred to the user / `/qa-agent`).

## Acceptance Criteria

- [x] `/handoff` skill exists and is registered (symlinked) as a slash command.
- [x] SessionStart hook injects `HANDOFF-latest.md` via `additionalContext` on
      `startup`/`resume`/`clear`.
- [x] Hook skips `source=compact` (same session already holds context).
- [x] Hook dedupes per `(content-hash, session_id)`; a NEW handoff resets dedupe.
- [x] Hook is cwd-scoped and NEVER raises into the harness (always exit 0, clean
      stdout on every degenerate path).
- [x] Optional Stop hook is NON-blocking (no `decision` field) and de-duplicated
      per session per 10% band.
- [x] Hooks are stdlib-only and run under plain `python3` (no `uv`/dep risk).
- [x] mypy clean, ruff clean, 36/36 tests pass (23 handoff + 13 learnings-log).
- [x] Guide doc records the design + feasibility review; ephemeral files
      git-ignored (README tracked).

## Implementation Plan

1. `scripts/handoff/constants.py` — shared constants + env resolution.
2. `scripts/handoff/inject_handoff.py` — SessionStart injection hook.
3. `scripts/handoff/context_reminder.py` — optional non-blocking Stop nudge.
4. `skills/handoff-skill/SKILL.md` — model-driven `/handoff`.
5. Tests, gitignore, `.agent/handoff/README.md`, `docs/guides/smart-handoff.md`.
6. Wire `~/.claude/settings.json` + symlink the skill.

## Files Touched

See `.agent/reports/AE-0216.dev-summary.md`.

## Test Evidence

```bash
uv run --project backend python -m pytest scripts/handoff/tests/ -q   # 36 passed
uv run --project backend mypy scripts/handoff/*.py                    # Success
uv run --project backend ruff check scripts/handoff/                  # All checks passed
```

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-18

Researched feasibility (architect research mode: 3 parallel read-only threads),
ran an external cross-LLM cold-critic review (opencode → glm-5.1, after
gemini-3-pro-preview was decommissioned and gemini-2.5-pro hallucinated).
Verified the SessionStart/Stop hook contract against the live docs. Built the
three pieces, wired config, tests green.

### 2026-06-18 (extension — kaizen in the loop)

Closed the handoff → improvement loop. `/handoff` now appends distilled learnings
to `.agent/handoff/learnings-log.jsonl` via `scripts/handoff/log_learnings.py`;
the SessionStart hook nudges a fresh session to run `/kaizen-skill session` when
unreviewed learnings exist (watermark-gated). Added kaizen **`session` mode**
(SKILL.md + config.yaml + signal-sources.md) that mines the learnings log as a
first-class Phase-0 signal source — proposing lint/gate/doc/CLAUDE.md/bugfix
enforcements, still behind the mandatory Phase-4 approval gate (ratchet UP only).
Tested end-to-end: logged this session's learnings → nudge fired (pending=1) →
ran a scoped `session` pass producing `.agent/reports/kaizen-session-2026-06-18.plan.md`
with 4 verified proposals (K1–K4), stopped at approval. 36/36 tests, mypy+ruff clean.

## Decision Log

- **Rejected full auto-trigger.** External review confirmed Stop-hook "block"
  forces continuation, not a pause; a hook cannot force a tool call; transcript
  `usage` parsing is undocumented/version-fragile. Kept model-driven generation
  + automatic re-injection; human triggers via the statusline they already have.
- **Inject on every source except `compact`.** Fresh session = `startup`,
  `/clear` = `clear`; compaction keeps the same session and must not be
  re-seeded. Dedupe keyed on content-hash so a new checkpoint re-offers once.
- **Plain `python3`, not `uv run`.** Scripts are stdlib-only; avoids `uv` sync
  latency and the risk of `uv` writing to stdout and corrupting the hook's JSON.
- **JSON twin for durable state.** Models overwrite Markdown more readily than
  strict JSON (Anthropic long-horizon-agents guidance).

## Blockers

None.

## Final Summary

Shipped the smart-handoff workflow as developer-harness tooling: a `/handoff`
skill writes a curated narrative + structured-JSON checkpoint to
`.agent/handoff/`; a never-raising, cwd-scoped, content-hash-deduped SessionStart
hook re-injects it into a fresh session (skipping compaction); an optional
non-blocking Stop hook nudges at ≥70% window. The fully-automatic trigger from
the original idea was deliberately dropped after an external feasibility review
showed it rested on a hook-semantics misconception. mypy/ruff clean, 23/23 tests
pass, validated end-to-end against the real wired hook command. Config wired in
`~/.claude/settings.json` + skill symlink (session restart needed to activate the
slash command). Not committed — left in the working tree for user review/QA.
