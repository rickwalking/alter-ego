# External QA Orchestration

## Why external

Same-session models grade their own work leniently and inherit the
author's blind spots (self-preference bias — same rationale as the
architect skill's cold critic). An external CLI session with repo
access but **no conversation context** validates from evidence only.
Wave 1 proof: the external QA caught a factual error in the developer's
own test-count evidence and three surviving mutants the author missed.

## Orchestrator

```bash
scripts/qa/run_external_qa.sh <prompt-file> <output-file> [opencode|codex|cursor]
```

Handles tool fallback (opencode → codex → cursor-agent), the OpenCode
hang-at-init recovery (clean-kill, stream health check, one retry),
ANSI stripping, and `QA_VERDICT` extraction. Exit codes: 0 PASS,
10 WARN, 20 FAIL, 2 no-verdict, 3 launch-failed.

Tool notes:

- **OpenCode**: use the `plan` (read-only) agent; it can read the repo
  and run verification commands. Known failure modes (observed
  2026-06-12): launches after an unclean exit hang at `init` (the
  script clean-kills first and health-checks the log for
  `stream providerID`); long runs can die mid-stream without emitting
  the report (the prompt's always-emit-verdict rule plus a tool-call
  budget mitigates).
- **Codex**: `codex exec --sandbox read-only` at repo root; subject to
  usage limits — treat quota errors as "fall back", not "retry".
- **Cursor**: `cursor-agent --print`; verify availability before
  relying on it in unattended runs.

## Prompt construction (mandatory elements)

1. Point at the skill: "Read skills/delivery/qa-agent/SKILL.md and
   follow its protocol and report format", plus mode (full/lite/wave).
2. Scope pin: ticket file(s), dev summary path(s), and the exact
   implementation commit hash(es) (`git show <sha>`).
3. Read-only declaration, with verification commands explicitly
   allowed (scripts, pytest, ruff — they don't modify tracked files).
4. Per-dimension instructions, including independent re-verification
   of every claim in the dev summary (re-run scripts, re-execute
   tests, diff against committed numbers). For measurement/docs
   tickets, replace the mutation dimension with
   **accuracy/reproducibility**; for code tickets, request analytical
   mutation analysis (survivors + the missing assertion that kills
   each) instead of running mutmut.
5. Context section: accepted gaps and owner decisions that are NOT
   findings (cite the ticket Decision Log).
6. Resilience rules: tool-call budget (10-20), "could not verify →
   record and move on" (one retry max), and **always end with the
   consolidated report + a final line `QA_VERDICT: PASS|WARN|FAIL`**,
   even if dimensions are INCONCLUSIVE.

## Verdict loop (run until quality is satisfied)

- **FAIL** → developer fixes → full external re-run.
- **WARN** → fix all actionable findings (same Dev→QA day where
  possible) → short **confirmation round**: a small prompt listing
  each finding, asking RESOLVED/NOT-RESOLVED with evidence plus
  any-new-issues, budget ~6 tool calls. Repeat until PASS.
- **PASS** → archive and move ticket(s) to Review.

## Archiving and board protocol

1. Save the cleaned report to `.agent/reports/<scope>.qa.md` with a
   **provenance block**: tool, provider/model, agent mode, round
   summaries, fix commit hashes, date, and any operational incidents.
2. Append a **post-QA fix addendum** documenting what was fixed vs
   accepted/deferred (with owners) — findings must never silently
   vanish.
3. `validate_all_tickets.py` requires a per-ticket
   `.agent/reports/AE-####.qa.md` before Review status: for wave-level
   QA, write thin per-ticket pointer files referencing the wave report.
4. Update each ticket's QA Report section and QA Checklist, move to
   Review (warnings-resolved or pass), re-render the board.

## Live progress monitoring (OpenCode)

- Lifecycle: `tail -f ~/.local/share/opencode/log/opencode.log` —
  healthy runs show `stream providerID=... modelID=...` within seconds
  of launch; `init` followed by silence means hung.
- Tool-call feed: the session DB shows what the reviewer is doing in
  real time:

  ```bash
  sqlite3 ~/.local/share/opencode/opencode.db \
    "SELECT json_extract(data,'$.tool'),
            substr(json_extract(data,'$.state.input.description'),1,80)
     FROM part ORDER BY id DESC LIMIT 10"
  ```
