---
name: kaizen-skill
description: "Continuous-improvement / retrospective harness. Turns recurring quality signal (CI failures, QA reports, code-reviewer comments, integrity warnings, debt markers) into systemic fixes: root-cause analysis, external best-practice research, and concrete rule/gate/doc/lint enforcement — proposed, approved by a human, then auto-emitted as tickets. Use when the user says 'run kaizen', 'retro on AE-####', 'why does this keep failing', 'improve our rules', or on a schedule. Evolves the project's quality bar UP over time. Never use to implement feature code or to loosen a gate."
version: 1.0.0
disable-model-invocation: true
---

# Kaizen Skill — feedback → systemic enforcement

## Purpose

Close the delivery loop. Where `qa-agent` stops gaming **inside one PR**, this
skill stops the same failure **class** from recurring across PRs by evolving the
project's rules. It ingests recurring signal (CI failures, `.agent/reports/*.qa.md`,
code-reviewer comments, `check-integrity.sh` warnings, suppression/debt markers),
finds the root cause, researches the best-practice fix, maps the exact
doc/rule/gate/linter changes, and — after **human approval** — auto-creates
enforcement tickets via `ticket-writer-skill`.

It is the feedback arm of `planner → architect → ticket-writer → developer →
qa-agent → release-manager`, feeding improvements back to the front of the chain.

## THE INVARIANT — ratchet up, never down

> **Every proposal must raise or hold the quality bar. A proposal that loosens a
> threshold, adds an ignore/suppression, weakens a gate, or removes a check is
> rejected by construction.** The fix for "tests keep failing the mutation gate"
> is stronger tests or a refactor — never a lower gate.

This is the mirror of the guardian (`qa-agent`): the guardian stops a developer
gaming a gate in a PR; Kaizen stops the *rules themselves* from being gamed over
time. Synthesis (Phase 3) drops any down-ratchet proposal and records why.

## Modes

| Mode | Invoke | When |
|------|--------|------|
| **incident** (default) | `/kaizen-skill AE-####` or `/kaizen-skill <PR#>` | one ticket/PR/failure produced a finding worth generalizing |
| **sweep** | `/kaizen-skill sweep` | scheduled (weekly) — aggregate accumulated signal across the repo for patterns |

Scheduling: run `sweep` weekly via the `schedule` skill (cloud routine) or a
GitHub Actions `schedule:` workflow. Suggested cadence: weekly, off-hours.

### Execution model — local vs external (cost)

Either mode can run two ways:

- **local** (default): the analysis subagents run in this session.
- **external** (`/kaizen-skill <scope> external`): the token-heavy analysis
  (Phases 0–2) is offloaded to a cheaper external LLM CLI via
  `scripts/kaizen/run_external_kaizen.sh`, the same way `qa-agent` offloads
  review. It shares the hardened runner mechanics (`scripts/lib/external_agent.sh`).
  The external run is **read-only and produces the plan + a proposals block**;
  the main session then does the steps below that must stay trusted and local:
  **invariant re-validation → Phase 4 approval → Phase 5 emission**.
  Full runbook + prompt contract: `references/external-kaizen.md`.

  > **Defense in depth:** the main session ALWAYS re-validates the ratchet
  > invariant on the returned proposals (drop anything that loosens a gate) —
  > the external model's self-assessment is advisory, never authoritative.

## Boundaries (do not overlap)

- **Not `architect-skill`** — architect designs ONE feature/bugfix. Kaizen
  analyses patterns ACROSS incidents and targets *rules/gates/process*. Kaizen
  MAY invoke `architect-skill research "<question>"` for a deep technical
  proposal, but it never writes a feature plan itself.
- **Not `ticket-writer-skill`** — Kaizen decides *what* to enforce; ticket-writer
  materializes the tickets. Kaizen calls it, never duplicates `create_ticket.py`.
- **Read-only on production code.** Kaizen produces reports + tickets, never edits
  source. (Its tickets later drive the developer skill.)

## Pipeline

All artifacts live under `.agent/reports/kaizen-<id>.*` where `<id>` is the
ticket/PR for incident mode or a date stamp (e.g. `sweep-2026-06-15`) for sweep.

### Phase 0 — Signal Collection (one collector subagent)
Gather and **cluster into failure classes** (not individual incidents). Full
source list + commands: `references/signal-sources.md`. In short:
- CI failures (`gh run list/view`, quality-gate job logs)
- QA reports (`.agent/reports/*.qa.md`) — recurring blocker/warning themes
- Code-reviewer comments (CodeRabbit / `gh pr view --comments`)
- `check-integrity.sh` history — repeated suppressions, apparatus edits, and
  every `# integrity-ok:` / `# noqa` / `# type: ignore` marker (each sanctioned
  exception is a candidate for a real rule)
- Debt markers (`TODO AE-####`, per-file-ignores, `ignore_errors` overrides)

Output `.agent/reports/kaizen-<id>.signal.md`: each failure class with
**frequency, severity, example file:line refs, and which gate (if any) should
have caught it**. Rank by frequency × severity.

### Phase 1 — Research Pack (one `Explore` subagent, cheap model)
Reuse the proven shared-pack pattern (`qa-agent/references/qa-research-pack.md`).
Write `.agent/reports/kaizen-<id>.research.md` covering the implicated areas so
downstream subagents **skip independent codebase exploration** (the dominant
token cost). Model selectable via `config.yaml` `research_pack.model`.

### Phase 2 — Analysis (parallel subagents; inject the pack as shared prefix)
Launch simultaneously; each reads only its pack sections and re-verifies facts
against live code before asserting (anti-blind-spot, per the pack's independence
mandate).

- **Subagent A — Root-cause + Fix Research.** Per top failure class: *why* it
  recurs (5-whys), then external best-practice research (WebSearch/WebFetch
  allowed) for the durable fix. Propose a **systemic enforcement** (new
  gate/lint rule/ADR/refactor/test pattern), not a one-off patch. **Self-check
  the invariant**: if the only "fix" is loosening, say so and escalate instead.
- **Subagent B — Rule & Doc Mapper.** For each proposed fix, name the **exact**
  edits: `CLAUDE.md` / `backend|frontend AGENTS.md` rules, `pyproject.toml` /
  `eslint.config` / `.importlinter` gate additions, new `scripts/ci/gates.sh`
  gate or `check-integrity.sh` pattern, `docs/decisions/` ADR, `docs/guides/`
  updates. Flag conflicts with existing rules/ADRs.

### Phase 3 — Synthesis → Improvement Plan
Merge A+B into `.agent/reports/kaizen-<id>.plan.md`, ranked. Per proposal:
failure class → root cause → proposed enforcement → exact files → effort (T1–T3)
→ **ratchet-direction = UP/HOLD** (drop any DOWN with reason) → expected signal
it eliminates. Include a "rejected (would loosen)" section for transparency.

### Phase 3.5 — Invariant re-validation (mandatory when run externally)
If Phases 0–2 ran externally, re-check every returned proposal in
`<output>.proposals.json` locally BEFORE approval: drop/flag any with
`ratchet != up|hold`, and reject any whose file edits would lower a threshold,
add a suppression/ignore, or raise an `import_baseline` ceiling (the same
patterns `check-integrity.sh` blocks). The external model's self-assessment is
advisory; this local check is authoritative. (Local runs do this inline in
Phase 3.)

### Phase 3.6 — External skeptical validation (standard, before approval)
Run the emitted plan + draft tickets through the architect **cold critic**
(`/architect-skill skeptical` → `scripts/lib/external_agent.sh`) as a STANDARD
step. A same-session review rubber-stamps its own analysis; the external critic
does not. Proven value (2026-06-17): it caught two factual errors kaizen had
shipped — a substring-grep false positive (`fetch(` matched `refetch(`) and a
wrong "gate today" claim (`lint:changed` uses `--quiet`, so warn-rules are
unenforced). Feed it a **blind packet** (plan + ticket specs, no author voice)
with `prompts/cold-critic-system.md`; **verify each finding against live code**
(advisory, not authoritative); resolve/waive each in the ticket `Decision Log`.
Skip only for T0/T1 trivia.

### Phase 4 — Human Approval Gate (mandatory)
Present the ranked plan (with the Phase 3.6 findings + resolutions) and **stop for
explicit approval**. The human may accept all, a subset, or defer items. Nothing
is created before approval.

### Phase 5 — Task Emission (orchestrator → ticket-writer)
For each **approved** proposal, call `ticket-writer-skill` to create a ticket:
```bash
uv run python scripts/agent_tasks/create_ticket.py \
  --title "<enforcement>" --tier <T1|T2|T3> --type "Quality" --area <backend|frontend|Cross-cutting>
uv run python scripts/agent_tasks/validate_ticket.py AE-####
uv run python scripts/agent_tasks/render_board.py
```
Each ticket's Problem cites the failure class + example refs from the signal
report; Acceptance Criteria state the new gate/rule and "the gate fails on a
seeded violation" (prove the enforcement works). Link back to
`.agent/reports/kaizen-<id>.plan.md`.

## Output report header

```markdown
# Kaizen Report — <id>
Mode: incident|sweep | Generated: <ts> | Signal window: <range>

## Failure Classes (ranked)
| # | Class | Freq | Severity | Gate that should catch it | Status |

## Proposals (approved set)
### P1 — <title>  [ratchet: UP]
- Failure class / root cause / external evidence
- Enforcement: <new gate|lint|rule|ADR> — exact files
- Ticket: AE-####

## Rejected (would loosen the bar)
- <proposal> — reason

## Tickets created
- AE-#### — <title>
```

## References

- `references/signal-sources.md` — how to gather & cluster each signal
- `references/external-kaizen.md` — external (cost-offload) orchestration runbook
- `scripts/kaizen/run_external_kaizen.sh` — external runner (shares the QA mechanics)
- `scripts/lib/external_agent.sh` — shared external-CLI mechanics (with run_external_qa.sh)
- `config.yaml` — signal sources, models, the ratchet invariant
- `qa-agent/references/qa-research-pack.md` — the reused shared-pack pattern
- `scripts/ci/gates.sh` / `scripts/ci/check-integrity.sh` — signal AND enforcement targets
- `ticket-writer-skill/SKILL.md` — ticket emission (Phase 5)
- `architect-skill` (research mode) — optional deep technical proposal
- `docs/guides/qa-checkpoints.md` — current gate inventory
