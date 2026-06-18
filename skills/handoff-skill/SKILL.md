---
name: handoff-skill
description: "Smart session handoff / smart compact. Use when the user says 'handoff', '/handoff', 'checkpoint this session', 'smart compact', 'context is getting full', or when the statusline / a Stop-hook reminder shows the context window is large (~70%+). Writes a curated, structured handoff of the CURRENT session (mission, problems+root-causes, decisions+rationale, current state, next steps, landmines) to .agent/handoff/ so a FRESH session (after /clear) is auto-re-seeded by the SessionStart hook. Prefer this over letting /compact run, because /compact is lossy-on-lossy. Read-only on production code."
version: 1.0.0
disable-model-invocation: true
---

# Handoff Skill (smart compact)

## Purpose

Capture everything this session learned **before** the context window fills, so
work can continue in a clean session without losing knowledge. This is the
**write-side** of smart handoff. The read-side is automatic: after you `/clear`
(or open a new session), `scripts/handoff/inject_handoff.py` re-injects the
handoff via the SessionStart hook.

**Why not just `/compact`?** `/compact` keeps the same session and is lossy
compression on top of lossy compression — rationale and early constraints die
first. A curated handoff + the already-auto-loaded memory/`.agent` files
preserves far more. See `docs/guides/smart-handoff.md` and ADR research in the
AE-0216 ticket.

## When to run

- The statusline or a Stop-hook reminder shows context ≳ 70%.
- You are about to hit a natural task boundary and want a clean slate.
- The user explicitly asks for a handoff / checkpoint / smart compact.

Run it **while you still have headroom** — generating the handoff itself costs
tokens, and you want it written from full context, not after auto-compact has
already fired.

## What to produce

Write **two twin files** into `<repo>/.agent/handoff/`:

1. `HANDOFF-latest.md` — the human- and model-readable narrative. **This is what
   gets injected** into the next session, so it must be self-sufficient.
2. `HANDOFF-latest.json` — the machine-readable structured twin (durable state
   that must not be paraphrased away). Use JSON, not prose, for the state that
   matters most; models overwrite Markdown more readily than strict JSON.

Overwrite both each time (they are `*-latest`). Writing new content auto-resets
the injection dedupe (the hook keys on content hash), so the next fresh session
picks up the new checkpoint exactly once.

## Procedure

1. **Gather state from your live context first** — you ARE the session; do not
   parse the transcript. Recall: what you were asked to do, what you tried, what
   broke and *why*, what you decided and *why*, what is done vs pending.
2. **Cross-check durable sources** (read-only):
   - `.agent/active-task.md` and the active ticket in `.agent/tasks/` — current
     ticket, status, acceptance criteria progress.
   - `git status` / `git branch --show-current` / recent commits — branch, WIP,
     uncommitted work, open PRs (`gh pr list` if relevant).
   - The repo `MEMORY.md` index — so the handoff does not duplicate facts already
     persisted as memory; instead, **promote** any durable, reusable learning to
     a memory file and merely reference it here.
3. **Write `HANDOFF-latest.json`** with the schema below.
4. **Write `HANDOFF-latest.md`** as the narrative (the gold-standard shape is the
   long handoff documents this project already uses: numbered sections, "the big
   pains", landmines, exact commands/paths).
5. **Append the learnings to the kaizen signal log** (deterministic helper):
   ```bash
   python3 scripts/handoff/log_learnings.py "$(pwd)"
   ```
   This distils `problems` / `landmines` / `decisions` from the JSON into an
   append-only `.agent/handoff/learnings-log.jsonl` — the signal that
   `/kaizen-skill session` later mines to propose systemic improvements. It is
   idempotent per handoff, so running it twice is safe.
6. **Tell the user** it is written and that they can now `/clear` (same terminal)
   or open a fresh session to continue — the SessionStart hook re-seeds it and,
   if learnings have piled up, nudges to run `/kaizen-skill session`. Do **not**
   run `/clear` yourself; that is the human's call.

## Relation to kaizen (the improvement arm of the loop)

The handoff is the **memory** arm; kaizen is the **improvement** arm. Every
handoff feeds `learnings-log.jsonl`; `/kaizen-skill session` turns accumulated
learnings into proposed lint rules / gates / `CLAUDE.md` + doc updates / bugfix
tickets (human-approved before anything is created). You do not need to run
kaizen here — the fresh session is nudged to, where it has full context budget.

## JSON schema (`HANDOFF-latest.json`)

```json
{
  "created_at": "<ISO-8601, ask the harness or use a shell `date` call>",
  "repo": "alter-ego",
  "branch": "<git branch>",
  "head_sha": "<short sha>",
  "mission": "One paragraph: what this session set out to do and where it got to.",
  "problems": [
    {"problem": "...", "root_cause": "...", "solution": "...", "status": "fixed|open|workaround"}
  ],
  "decisions": [
    {"decision": "...", "rationale": "..."}
  ],
  "current_state": {
    "active_ticket": "AE-####|none",
    "wip": "what is half-done right now",
    "open_prs": ["#NN ..."],
    "uncommitted": "summary of working-tree changes"
  },
  "next_steps": ["ordered, concrete, the first thing the next session should do"],
  "landmines": ["things that will bite — do NOT do X; Y looks done but isn't"],
  "open_questions": ["unresolved decisions awaiting the user"],
  "files_touched": ["path — why"],
  "verification": ["exact commands to confirm state, e.g. uv run pytest ..."],
  "related_memory": ["memory-file-slug — what it covers"]
}
```

## Quality bar

- **Capture the *why*, not just the *what*.** Rationale and dead-ends are the
  first thing lost to compaction and the most expensive to rediscover.
- **Landmines are mandatory** if any exist (e.g. "merging to main auto-deploys
  prod"). These are the highest-value lines in a handoff.
- **Be concrete**: real paths, real commands, real ticket IDs, real SHAs.
- **Stay under ~24k characters** in the markdown (the injection cap). If the
  session is huge, summarise older threads and keep the forward-looking detail.
- **Promote, don't duplicate**: durable cross-session facts belong in the
  `memory/` system; the handoff is for *this* session's in-flight state.

## Critical rules

- Read-only on production source — this skill only writes under `.agent/handoff/`
  (and may add a `memory/` file when promoting a durable learning).
- Never run `/clear` or start a new session for the user.
- Never wrap the write in a way that could fail silently — confirm both files
  were written and report their paths.
