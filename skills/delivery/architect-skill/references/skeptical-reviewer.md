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

## Config

See `../config.yaml` for CLI hints per tool.
