# External Kaizen Orchestration

## Why external

Kaizen's analysis (Phase 0 signal gather, Phase 1 research pack, Phase 2
root-cause + rule-mapping) is **read-heavy** — exploring the codebase and
existing rules is the dominant token cost. Offloading it to a cheaper external
LLM CLI (OpenCode / Codex / Cursor) cuts that cost the same way `qa-agent` does.
A fresh-context external model also avoids the main session's context bloat.

Unlike QA (where external = *bias* reduction), here external = *cost* reduction.
The trade is the same: **the trusted, repo-writing, human-gated steps stay local.**

## What runs where

| Phase | Where | Why |
|-------|-------|-----|
| 0 Signal · 1 Research pack · 2 Analysis | **External** (read-only) | token-heavy, no writes |
| 3 Synthesis (final ranked plan) | local (cheap merge) | small, formats for the human |
| **Invariant re-validation** | **local (mandatory)** | never trust the external model to self-police |
| 4 Approval gate | local (human) | decision authority |
| 5 Ticket emission | local | writes the repo |

## Orchestrator

```bash
scripts/kaizen/run_external_kaizen.sh <prompt-file> <output-file> [opencode|codex|cursor]
```
Shares `scripts/lib/external_agent.sh` with `run_external_qa.sh` (tool fallback,
OpenCode hang-recovery, ANSI strip). Exit codes: 0 = plan + proposals produced,
2 = no proposals block (run died mid-stream), 3 = launch failed after retry.
Extracts the proposals block to `<output-file>.proposals.json`.

## Prompt construction (mandatory elements)

1. **Skill pointer:** "Read `skills/delivery/kaizen-skill/SKILL.md` and
   `references/signal-sources.md`; perform Phases 0–2 only." State mode
   (incident/sweep).
2. **Scope pin:** the PR number / ticket id / date window, and the base ref.
3. **Read-only declaration**, with verification commands explicitly allowed:
   `gh` (PR comments, run logs), `grep`/`cat`, `scripts/ci/check-integrity.sh`.
   It must NOT edit tracked files or create tickets.
4. **THE INVARIANT (state it loudly):** propose only fixes that *raise or hold*
   the quality bar. A proposal that loosens a threshold, adds a suppression, or
   weakens/removes a gate is forbidden and must instead be listed under
   `rejected`. (The main session re-checks this regardless — see below.)
5. **Per-phase instructions:** cluster signal into failure classes ranked by
   frequency × severity; build the research pack; for each top class give
   root-cause (5-whys) + best-practice fix + the exact rule/doc/gate files to
   change.
6. **Output contract:** write the full plan report (the `## Failure Classes`,
   `## Proposals`, `## Rejected` sections per SKILL.md), and end with a single
   fenced `json` **KAIZEN_JSON** block the runner extracts:

   ```json
   { "scope": "pr21", "mode": "incident",
     "failure_classes": [ {"id":"C1","title":"...","freq":13,"severity":"high","gate":"none"} ],
     "proposals": [ {"id":"P1","title":"...","ratchet":"up","effort":"T2",
                     "area":"frontend","type":"Task",
                     "files":["frontend/scripts/check-component-types.mjs"],
                     "eliminates":"C1"} ],
     "rejected": [ {"title":"lower audit-level","reason":"loosens the bar"} ] }
   ```
   Every proposal MUST carry `ratchet: up|hold|down`. (`down` should already be
   under `rejected`; if one appears in `proposals`, the local re-validation drops it.)
7. **Resilience:** tool-call budget 20–30; "could not verify → record and move
   on" (one retry); ALWAYS end with the KAIZEN_JSON block even if analysis is
   partial.

## Local re-validation (mandatory — defense in depth)

After the external run returns, the main session — NOT the external model —
re-validates every proposal in `<output>.proposals.json`:

- Drop / flag any proposal with `ratchet != up|hold`.
- Cross-check the named file edits: any that would lower a `fail_under` /
  threshold, add a `per-file-ignores` / `ignore_errors` / suppression, or raise
  an `import_baseline` ceiling is rejected — same patterns `check-integrity.sh`
  blocks. **The external model's self-assessment is advisory; this check is
  authoritative.**
- Only surviving, UP-ratchet proposals reach the Phase 4 approval gate.

Then proceed with the normal local Phase 4 (approval) and Phase 5 (emit tickets
via `ticket-writer-skill`).

## Loop / reuse

For `sweep` mode, run this weekly (schedule skill / GH Actions). The external
run is stateless; the main session archives the plan to
`.agent/reports/kaizen-<id>.plan.md` and emits tickets exactly as in the local flow.
