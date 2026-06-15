# Wave Loop — batch dev + automated external QA

Implement a **group of related tickets** ("wave"), then run an automated
`dev → QA → fix → re-QA` loop against an **external** reviewer until the wave
converges to PASS or a safeguard escalates to a human.

## When to use

- Several Ready tickets that belong together (e.g. Wave 2 = AE-0071, AE-0072,
  AE-0073, AE-0076) and benefit from one integrated QA pass.
- The human asked to "complete the wave, QA, fix, re-QA until ready".

For a single ticket, use the default single-ticket SDD flow instead.

## Step 1 — Order the wave (topological sort)

1. Read each ticket's `Blocked-by` / `Blocks` (or Dependencies) fields.
2. Topologically sort (Kahn's algorithm). Tickets at the same depth are
   parallel-safe; implement in dependency order regardless.
3. If a cycle exists, stop and escalate — the wave is mis-specified.

## Step 2 — Implement the whole wave

Run the standard SDD loop (spec → implement → test → self-verify → commit) for
each ticket in dependency order. Implement the **entire wave before QA** so the
external pass can catch cross-ticket integration issues. Update each ticket's
Progress Log and move to `Dev Complete`; write per-ticket dev-summaries.

## Step 3 — External QA (batch, tagged by ticket)

One QA pass over the whole wave (cheaper, catches integration issues), with
findings tagged per ticket:

```bash
scripts/qa/run_external_qa.sh <wave-prompt> <out> [tool]
```

Build the wave prompt per `skills/delivery/qa-agent/references/external-qa.md`
(wave mode): point at the qa-agent skill, pin the implementation commit(s),
list every ticket + its AC, require findings tagged with `ticket:` and the
final `QA_VERDICT:` line + optional JSON findings block (below).

## Step 4 — The loop

```python
MAX_ITERATIONS = 5     # hard cap; past ~5-6 rounds, review ADDS noise
MIN_ITERATIONS = 2     # round1 ≈ 50% of gains, round2 ≈ 25% → never trust a single pass
seen_fingerprints = set()
prev_count = None
first_fail_seen = False

wave = topo_sort(tickets)
dev_implement(wave)                       # whole wave first

for i in range(1, MAX_ITERATIONS + 1):
    qa = run_external_qa(wave)            # external model + fresh context

    if qa.verdict == "PASS":
        if i >= MIN_ITERATIONS:
            conf = run_external_qa(changed_files_only)   # verify-only confirmation round
            if conf.verdict == "PASS":
                return DONE
            qa = conf
        else:
            continue                       # force the 2nd independent pass

    # --- verdict is WARN or FAIL ---
    if qa.verdict == "FAIL" and not first_fail_seen:
        first_fail_seen = True
        PAUSE_FOR_HUMAN("first FAIL of this wave — review the loop before continuing")

    fps = fingerprints(qa.findings)        # hash(normalized file + rule + message)
    if fps & seen_fingerprints:
        return ESCALATE("repeated finding — looping can't fix it: " + str(fps & seen_fingerprints))
    if prev_count is not None and len(qa.findings) >= prev_count:
        return ESCALATE("no progress between rounds (plateau)")
    seen_fingerprints |= fps
    prev_count = len(qa.findings)

    dev_fix(blockers(qa))                  # fix FAIL-severity; WARN/minor optional
    if files_moved():
        regenerate_research_pack()         # staleness guard (qa-research-pack.md)

return ESCALATE("max iterations reached without clean PASS")
```

## Safeguards (why each exists)

| Safeguard | Rule | Source |
|-----------|------|--------|
| Minimum passes | Run ≥ 2 QA passes even on early PASS | round1≈50%, round2≈25% of gains (Yang 2025) |
| Hard cap | Stop at 5 iterations | past ~5-6, review adds noise (arXiv 2603.16244) |
| Oscillation | Repeated finding fingerprint → escalate | actor-critic drift guard |
| Plateau | Findings count not dropping → escalate | diminishing returns |
| Confirmation | Final verify-only pass, changed files only | cheap robust convergence check |
| Pause on 1st FAIL | Human checks the loop once per wave | operator decision (2026-06-12) |
| Critic scope | Blockers = correctness/requirements gaps only | prevents WARN-noise from blocking PASS |

PASS ⇔ zero FAIL-severity (critical) findings. WARN/minor are non-blocking;
fix the actionable ones but do not let them prevent convergence.

## Verdict contract (handoff shape)

External QA must end with `QA_VERDICT: PASS|WARN|FAIL`, and SHOULD also emit a
JSON findings block the loop parses for fingerprints/plateau detection:

```json
{ "verdict": "PASS|WARN|FAIL", "wave_id": "wave-2", "iteration": 2,
  "findings": [ {"id":"F-101","severity":"critical","ticket":"AE-0072",
                 "file":"src/...","line":42,"problem":"...","fix":"..."} ],
  "summary": {"critical":0,"warning":1,"minor":3} }
```

If no JSON block is present, fall back to the verdict line + textual findings
(current behaviour) — fingerprint on `file+message` text instead.

## Board protocol per round

- On FAIL/WARN with fixes: keep tickets in `Needs Fixes`, log the round in each
  ticket's Progress Log with the QA report path + round number.
- On converged PASS: write/refresh per-ticket `.agent/reports/AE-####.qa.md`
  (thin pointers to the wave report for batch QA), move tickets to `Review`,
  re-render the board. See `qa-agent/references/external-qa.md` archiving rules.
- On escalation: leave tickets in `Needs Fixes`/`Blocked`, record the
  escalation reason, and hand the wave report to the human.
