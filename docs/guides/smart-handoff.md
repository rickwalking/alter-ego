# Smart Session Handoff (smart compact)

> AE-0216. A workflow for continuing a long Claude Code session in a **fresh**
> session without losing accumulated learnings — a higher-fidelity alternative to
> letting `/compact` run repeatedly.

## The problem

`/compact` (manual or auto) keeps the *same* session and summarises older
history in place. It is **lossy compression on top of lossy compression**: across
cycles, decision *rationale*, early constraints ("don't touch X"), and exact
error trails are the first things to disappear. For a long, high-stakes session
(e.g. a prod-incident debugging marathon) that loss is expensive.

We already have durable, cross-session memory (`MEMORY.md` + `memory/` files,
the `.agent/` ticket system, `CLAUDE.md`). The gap is the **in-flight
conversational state** of a single session — the "why we did what we did" that
hasn't yet been promoted to a memory file. Smart handoff captures exactly that.

## The design (and what we rejected)

The original idea was full automation: a hook detects the context window getting
large, auto-generates a handoff, and auto-starts a seeded fresh session. A
research pass (architect-skill research mode) plus an **external cross-LLM
feasibility review** (cold-critic) found the fully-automatic trigger rests on a
misconception, so we built the robust subset instead.

What the review established about Claude Code's actual hook contract:

| Mechanism | Reality |
|---|---|
| Context % visible to a hook | Only by parsing the transcript `.jsonl` `usage` fields (undocumented, version-fragile). Usable for a *nudge*, not as a hard trigger. |
| `Stop` hook "block" | Forces Claude to **continue generating** — it does **not** pause for a handoff. Cannot be the trigger. |
| A hook forcing the model to run a skill | Not possible — hooks emit text/context, they cannot force a tool call. |
| `SessionStart` `additionalContext` | **Real and documented.** Injected into the new session. `source` ∈ {startup, resume, clear, compact}. Multiple hooks per event run in series and concatenate. |
| Auto-spawn a seeded new session | No documented CLI flag. The human starting the session (or `/clear`) is the one true seam. |

**Conclusion:** drop auto-trigger; keep model-driven generation + automatic
re-injection. The human watches the statusline (they already have it) and runs
one command.

## The three pieces

1. **`/handoff` skill** (`skills/handoff-skill/`) — model-driven, manual. Writes
   a curated `HANDOFF-latest.md` (narrative, injected) + `HANDOFF-latest.json`
   (structured durable state) into `.agent/handoff/`. JSON for must-not-lose
   state because models overwrite Markdown more readily than strict JSON
   (Anthropic long-horizon-agents guidance).

2. **SessionStart injection hook** (`scripts/handoff/inject_handoff.py`) — on a
   fresh/resumed/cleared session, re-injects the latest handoff as
   `additionalContext`. Skips `source=compact` (same session already holds the
   context). Dedupes per `(handoff-content-hash, session_id)` so a session is
   seeded at most once per handoff, and a **new** handoff (different hash)
   auto-resets the dedupe. Never raises into the harness.

3. **Optional Stop reminder** (`scripts/handoff/context_reminder.py`) — the
   *safe* version of auto-detect. Non-blocking: at ≥70% window utilisation it
   injects a one-time `additionalContext` nudge ("consider `/handoff` then
   `/clear`"), de-duplicated per session per 10% band. It never blocks and never
   forces a tool call.

## The loop

```
long session → statusline (or Stop nudge) shows ~70% → /handoff (writes .agent/handoff/)
            → /clear  (same terminal; source=clear)
            → SessionStart hook re-injects HANDOFF-latest.md → continue in fresh context
```

`/clear` in the same terminal is the cheapest "fresh session": it fires
SessionStart with `source=clear`, which the injection hook handles.

## Configuration

Hooks live in `~/.claude/settings.json` (user-global, outside the repo):

```jsonc
{
  "hooks": {
    "SessionStart": [
      { "hooks": [ { "type": "command",
        "command": "python3 /home/pmarins/projects/alter-ego/scripts/handoff/inject_handoff.py" } ] }
    ],
    "Stop": [
      { "hooks": [ { "type": "command",
        "command": "python3 /home/pmarins/projects/alter-ego/scripts/handoff/context_reminder.py" } ] }
    ]
  }
}
```

The `/handoff` skill becomes a slash command via a symlink:
`~/.claude/skills/handoff-skill → skills/handoff-skill` (then restart the session).

Env overrides: `HANDOFF_CONTEXT_WINDOW` (default 200000),
`HANDOFF_REMINDER_THRESHOLD` (default 0.70).

## Limits / honesty

- The reminder's % is derived from undocumented transcript fields; if a Claude
  Code update renames them it silently reads 0 and simply stops nudging (it never
  misfires destructively — worst case is no reminder, and the statusline still
  works the same way).
- The window size is a fixed default (200k); a 1M-context model under-reports %.
  Set `HANDOFF_CONTEXT_WINDOW` to match if needed.
- This complements — does not replace — the `memory/` and `.agent/` systems.
  Promote durable learnings to `memory/`; use the handoff for one session's
  in-flight state.

## Tests

`scripts/handoff/tests/` (stdlib + pytest, run with
`uv run --project backend python -m pytest scripts/handoff/tests`). Covers
inject (dedupe, skip-on-compact, new-handoff reset, cwd scope, truncation,
never-raise) and the reminder (threshold, band dedupe, non-blocking, never-raise).
