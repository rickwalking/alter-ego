---
name: planner-skill
description: "Break fuzzy product or technical requests into epics, tickets, dependencies, and risks with acceptance criteria. Use for T3 epics before architect. Does not write code or modify production source."
disable-model-invocation: true
version: 1.0.0
---

# Planner Skill

## Purpose

Convert vague requests into actionable epics and ticket breakdown.

## Rules

- Do not write production code.
- Do not mark work Ready without acceptance criteria per ticket.
- Identify backend, frontend, docs, tests, migrations, prompts impact.
- Prefer vertical slices; one ticket ≈ one branch.
- Add explicit dependencies.

## Output

- Epic summary (in `docs/plans/` or ticket comment)
- Proposed ticket list with IDs, titles, tiers
- Risks and suggested order
- Handoff to `/architect-skill`

## References

- `docs/guides/ticket-writing-guide.md`
- `CLAUDE.md`
