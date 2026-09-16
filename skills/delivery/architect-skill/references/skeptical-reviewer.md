# Skeptical Reviewer (Cold Critic)

## Why external LLM

Same-session models agree with their own plans (self-preference bias). Use a **separate** CLI session with plan-only input.

## Blind packet

Include only:

- `.agent/reports/AE-####.arch-plan.md` or `docs/plans/<plan>.md`
- ADR IDs referenced (not full prose unless needed)

Exclude: chat history, author name, implementation diffs.

## Steps

1. Copy packet to temp file.
2. Run reviewer with `../prompts/cold-critic-system.md` as system prompt.
3. Paste result into `.agent/reports/AE-####.skeptical-review.md`.
4. Primary architect resolves findings in ticket `Decision Log`.

## Trigger when

- Plan "feels done" (comfort = trigger)
- T3 or `high_risk_areas` in `.agent/config.yaml`
- Human requests

## Convergence — when to STOP a multi-round loop (AE-0326)

The cold-critic system prompt **mandates ≥3 material findings per round**, so a
literal zero-findings verdict is structurally unreachable — do NOT loop waiting
for one, and do NOT weaken the ≥3-findings mandate to make it reachable (that
is the down-ratchet; the mandate is anti-rubber-stamp by design).

**Default stop rule: 3 consecutive rounds with zero BLOCKERs = converged.**
Track the severity trajectory (BLOCKER count per round), not the verdict text.
Empirical basis: the AE-0300..0307 security loop (stopped at rounds 7–9) and
the AE-0295..0299 loop (5 rounds) — n=2 sessions; revisit if a converged wave
later ships a blocker-class defect.

- The rule is a **default, not absolute**: stop earlier or later with a
  recorded justification in the review record (e.g. round 2 blockers were
  factual-error corrections, or the plan is T3 with irreversible steps).
- Calibration caveat: the BLOCKER/WARN boundary drifts across reviewer models —
  a reviewer downgrading a real blocker to WARN falsely signals convergence.
  When in doubt, verify WARN findings against live code before counting a
  round as zero-blocker.
- Each round adds new attackable text; past convergence, further rounds only
  polish prose forever (the AE-0300 loop's observed behaviour).

## Operational landmines

- prettier is **non-idempotent** on inline code spans wrapped across line
  breaks inside `.md` list items (`--write` "fixes", `--check` still fails):
  rejoin the code span onto one line in the source.
- Write reviewer OUTPUT to /tmp (not tracked `.agent/reports/`) and pass the
  prompt file by ABSOLUTE path — the runner cd's into a detached worktree and
  the `.wt.log` sidecar trips the AE-0170 guard otherwise. Copy results back
  after.

## Config

See `../config.yaml` for CLI hints per tool.
