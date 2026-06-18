# `.agent/handoff/` — smart session handoff

Working state for the **smart handoff / smart compact** workflow (AE-0216).

- `HANDOFF-latest.md` — curated narrative handoff of the most recent session.
  **Auto-injected** into a fresh session by the SessionStart hook
  (`scripts/handoff/inject_handoff.py`).
- `HANDOFF-latest.json` — machine-readable structured twin (durable state).
- `.consumed` / `.reminder` — hook bookkeeping (content-hash dedupe + Stop-hook
  nudge bands). Not human-edited.

These files are **session-ephemeral** and git-ignored (see `.gitignore`). To
write one, run `/handoff` (the `handoff-skill`). To continue afterwards, `/clear`
in the same terminal or open a new session — the handoff is re-seeded
automatically.

See `docs/guides/smart-handoff.md` for the full design and the feasibility
review that shaped it.
