# Plan — Dev & QA Skill Improvements (research-pack + automated wave loop)

**Status:** PROPOSED (not yet applied)
**Date:** 2026-06-12
**Author:** architect/claude
**Scope:** `skills/delivery/qa-agent/`, `skills/delivery/developer-skill/`, `scripts/qa/`

Two capabilities requested:

1. **QA orchestrator builds a shared `research.md` once**, then injects it into the
   5 QA subagents so they skip independent codebase exploration → lower token cost.
2. **Dev skill runs a wave loop**: implement a group of tickets, auto-invoke external
   QA, fix, re-QA — **QA → Dev → QA → Dev until no issues**, with convergence safeguards.

Both are grounded in the web research captured in this session (sources at bottom).

---

## Part A — QA shared research pack

### Problem
Today the 5 QA subagents (security, code-quality, mutation, AC, orphan) each re-read
the codebase. That is ~5 redundant exploration passes — and exploration is the single
biggest token cost driver (Anthropic: token usage explains ~80% of outcome variance;
multi-agent ≈ 15× a chat). One shared exploration removes ~4 of those passes.

### Design
**New Phase 1.5 in qa-agent: "Build the QA Research Pack."**

The orchestrator (or a cheap Explore subagent — Anthropic runs Explore on Haiku for
read-only synthesis) does ONE codebase pass over the change scope and writes
`.agent/reports/AE-####.qa-research.md` (or `<scope>.qa-research.md` for waves).

**research.md structure** (role-tagged so each reviewer reads only its slice; static
form of RCR-Router role routing):

```
# QA Research Pack — <scope> @ <commit-sha>
Generated: <ts> | Diff range: <base>..<head> | Regenerate-if: diff changes

## 0. Metadata & Freshness        [ALL]   commit SHA, branch, files-in-diff, base ref
## 1. Change Summary              [ALL]   what the change does, intent vs implementation (5 bullets)
## 2. File Inventory & Map        [ALL]   changed files + role; new/modified/deleted; entry points
## 3. Architecture & Data Flow    [security, code-quality]  component map, trust boundaries,
                                          external I/O (net/db/fs/subprocess), auth touchpoints
## 4. Conventions in Effect       [code-quality, AC]  CLAUDE.md/AGENTS.md rules that apply:
                                          constants policy, type strictness, 400-line/3-arg limits
## 5. Dependency Graph & Callers  [orphan, code-quality]  who-calls-what for changed symbols,
                                          public API surface, orphan candidates
## 6. Test Landscape              [mutation, AC]  existing tests touching code, coverage gaps,
                                          .feature files, fixtures, how to run
## 7. Risk Hot Spots              [ALL, per-dimension tags]  location + why risky + [tag]
## 8. Acceptance Criteria Mapping [AC]    each AC → file/symbol that should satisfy it; gaps
## 9. Glossary / Domain Terms     [ALL]
## 10. UNKNOWNS / NOT-VERIFIED    [ALL]   what the explorer could NOT confirm — anti-blind-spot
```

### How subagents consume it
Each of the 5 subagents receives:
- The pack as a **shared prefix** (identical across all 5 → prompt-cache hit; no re-read).
- A **short role brief** naming its relevant sections (security → §3,§7,§10; orphan → §5,§10;
  mutation → §6,§10; AC → §6,§8,§10; code-quality → §3,§4,§5,§7).
- An **independence mandate**: each reviewer MUST re-verify §10 unknowns and any pack claim
  it would fail a finding on. The pack is a starting map, not unchallengeable truth — this
  defeats the single-pass shared blind spot (Anthropic deliberately preserves per-subagent
  independent verification to reduce path dependency).

### Staleness guard
Pack is stamped with commit SHA + diff range. If the diff moves (a fix round changes files),
the orchestrator regenerates the pack (or just the changed sections) before re-running QA.

### Files changed (Part A)
- `skills/delivery/qa-agent/SKILL.md` — insert **Phase 1.5: Build QA Research Pack** before
  the parallel-subagent launch; update each subagent brief to "read the pack §X, do NOT
  re-explore, re-verify §10 + any claim you'd fail on."
- `skills/delivery/qa-agent/references/qa-research-pack.md` — NEW: the pack template above +
  generation instructions + role→section routing table + staleness rule. (Keeps SKILL.md
  under the 500-line guideline; references stay one level deep.)
- `skills/delivery/qa-agent/SKILL.md` References section — link the new file.

---

## Part B — Dev wave loop with automated external QA

### Problem
Dev skill handles one ticket, then hands off to a human to run QA. No batch ("wave")
processing and no automated dev→QA→fix→re-QA loop.

### Design
**New mode in developer-skill: "wave".** Given a set of tickets (e.g. Wave 2 =
AE-0071, AE-0072, AE-0073, AE-0076), the skill:

```
1. ORDER  — topological sort tickets by dependency (Blocks/Blocked-by). Same-depth = parallel-safe.
2. IMPLEMENT — run the existing SDD loop per ticket, in order, across the whole wave first.
3. QA      — call scripts/qa/run_external_qa.sh with a wave prompt (external model, fresh context).
4. LOOP    — read QA_VERDICT:
             FAIL → fix critical findings → regenerate research pack if files moved → re-run full QA
             WARN → fix actionable findings → confirmation round (verify-only, changed files)
             PASS → require >= 2 total passes, then a confirmation round → done
5. STOP    — on convergence OR a safeguard trip (below) → escalate to human.
```

### Convergence safeguards (the critical part — from Yang et al. 2025 + actor-critic sources)
- **MIN_ITERATIONS = 2** — run at least 2 independent QA passes even if the 1st says PASS
  (round 1 ≈ 50% of achievable gains, round 2 ≈ 25%; probabilistic verification needs 2 chances).
- **MAX_ITERATIONS = 5** — hard cap; beyond ~5–6 rounds review *adds* noise ("More Rounds,
  More Noise", arXiv 2603.16244). Hit the cap without PASS → escalate to human.
- **Oscillation guard** — fingerprint each finding (hash of normalized file+rule+message).
  If a fingerprint repeats across two iterations, the fixer can't resolve it by looping →
  stop and escalate that finding.
- **Plateau guard** — if findings count doesn't drop between rounds → escalate (diminishing returns).
- **Confirmation round** — final verify-only pass scoped to changed files, not the whole wave.
- **Critic instruction** — QA flags only correctness/requirements gaps as blockers; everything
  else is optional. Prevents WARN-noise from blocking convergence.

### Verdict contract (machine-readable handoff)
Extend the external QA output beyond the single `QA_VERDICT:` line with an optional JSON block
the loop can parse for fingerprints/severity:

```json
{ "verdict": "PASS|WARN|FAIL", "wave_id": "wave-2", "iteration": 2,
  "findings": [ {"id":"F-101","severity":"critical","ticket":"AE-0072",
                 "file":"...","line":42,"problem":"...","fix":"..."} ],
  "summary": {"critical":0,"warning":1,"minor":3} }
```
PASS = zero critical (FAIL-severity) findings. Backward-compatible: if no JSON block, the
loop falls back to the verdict line + textual findings (current behaviour).

### Why external + different model
Two independent axes both supported by research: **different model** (self-preference bias is
real) AND **fresh context** (Cross-Context Review beats same-session, p=0.004). Dev = Claude,
QA = opencode/codex/cursor → we get both. Already wired via `run_external_qa.sh`.

### Files changed (Part B)
- `skills/delivery/developer-skill/SKILL.md` — add **"Wave mode"** section: ordering, the
  loop, safeguards table, when-to-use; keep single-ticket flow as default.
- `skills/delivery/developer-skill/references/wave-loop.md` — NEW: full runbook (topo-sort
  rules, pseudocode loop, safeguard thresholds, verdict-JSON contract, escalation triggers,
  board updates per round). Keeps SKILL.md lean.
- `scripts/qa/run_external_qa.sh` — extend `extract_verdict` to also capture an optional JSON
  findings block (for fingerprint/plateau detection); new exit-code-preserving behavior.
  Add `--wave <id>` passthrough for prompt labeling. (Backward compatible.)
- `skills/delivery/qa-agent/references/external-qa.md` — document the JSON findings block and
  the wave-loop contract so dev and QA agree on the handoff shape.
- `skills/delivery/qa-agent/config.yaml` — add loop thresholds (min=2, max=5) and the
  verdict-JSON contract note as the single source of truth.

---

## Cross-cutting: skill-authoring conventions applied
- SKILL.md bodies stay under ~500 lines; heavy detail goes to `references/*` one level deep.
- Every loop states **explicit termination conditions + max iterations** in the skill text.
- Each subagent brief is **specific and non-overlapping** (vague briefs cause duplicate work).
- Pack generation is read-only; external QA is read-only + verification-commands only.

## Sequencing (suggested apply order)
1. Part A (research pack) — additive to QA, lowest risk, immediately cuts QA token cost.
2. `run_external_qa.sh` JSON extension + config thresholds — enables the loop.
3. Part B wave-loop reference + dev SKILL.md mode — the automation layer.
4. Dry-run on **Wave 2** (AE-0071→0072→0073→0076) as the first real exercise.

## Decisions (2026-06-12)
- **Q1 Explorer model → SELECTABLE subagent, NOT locked to Anthropic.** Pack-builder is a
  dedicated read-only subagent whose model is a config knob (`research_pack.model` in
  `config.yaml`), defaulting to a cheap/fast model but overridable (incl. non-Anthropic).
- **Q2 Loop autonomy → autonomous, pause on FIRST FAIL of each wave.** Runs dev→QA→dev
  unattended until PASS or a safeguard trip; pauses on the first FAIL so the human can
  sanity-check the loop before trusting it.
- **Q3 Wave QA granularity → batch, tagged by ticket.** One QA pass over the wave with
  per-ticket-tagged findings; re-QA only re-verifies tickets that had findings + dependents.

---

## Sources (web research, 2026-06-12)
- Anthropic — How we built our multi-agent research system
- Anthropic — Building agents with the Claude Agent SDK; Claude Code best practices
- RCR-Router (arXiv 2508.04903) — role-aware shared-memory routing
- DeputyDev (arXiv 2508.09676) — shared architectural context improves review F-score (59 vs 49)
- Iterative review-fix convergence formula (Yang et al. 2025, via dev.to/yannick555)
- Actor-Critic Adversarial Coding (understandingdata.com)
- Cross-Context Review (arXiv 2603.12123) + More Rounds, More Noise (arXiv 2603.16244)
- Nightshift batch framework (happycog.com); Reflexion; LangChain Reflection Agents
- Anthropic Agent Skills best practices + Claude Code skills/subagents docs
