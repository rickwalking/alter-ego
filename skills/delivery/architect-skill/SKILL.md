---
name: architect-skill
description: "Architecture hub: technical plans, ADR checks, optional validate/research/skeptical/bugfix modes. Use before implementation on T2/T3, high-risk areas, or when trade-offs need evidence. Read-only on production code unless explicitly switched to developer."
disable-model-invocation: true
version: 1.0.0
---

# Architect Skill

## Purpose

Validate technical approach and produce durable plan artifacts before development.

## Modes

| Mode | Invoke | Output |
|------|--------|--------|
| **plan** (default) | `/architect-skill` | `.agent/reports/AE-####.arch-plan.md` |
| **validate** | `/architect-skill validate` | `.agent/reports/AE-####.plan-validation.md` |
| **research** | `/architect-skill research "<question>"` | `.research.md`, `.options.md` |
| **skeptical** | `/architect-skill skeptical` | `.skeptical-review.md` (external LLM) |
| **bugfix** | `/architect-skill bugfix <paths>` | `.bugfix-design.md` |

Read mode details in `references/`.

## Tier routing

| Tier | Typical chain |
|------|----------------|
| T0 | Skip |
| T1 | `bugfix` only if root cause unclear |
| T2 | `plan` → optional `research` → `validate` |
| T3 | `plan` → `research` → `validate` → `skeptical` if high-risk |

## Core plan mode (default)

1. Read `CLAUDE.md`, relevant `AGENTS.md`, `docs/decisions/`, `docs/architecture/`.
2. Read ticket and any `docs/plans/*.md`.
3. Decide ADR required: yes/no; draft ADR path if yes.
4. Write `.agent/reports/AE-####.arch-plan.md`: modules, API contracts, data model, testing, rollout/rollback.
5. Update ticket `Decision Log`; handoff to ticket-writer or developer.

## Critical rules

- Do not edit production source in architect modes.
- Do not skip ADR check for architecturally significant changes.
- Research subagents are **read-only** (no parallel writes).
- Skeptical review uses **blind packet** — see `references/skeptical-reviewer.md`.

## Skeptical (cross-LLM)

1. Export plan-only markdown (no author voice).
2. Human runs external CLI (Codex, OpenCode, Claude Code) with `prompts/cold-critic-system.md`.
3. Save external output to `.agent/reports/AE-####.skeptical-review.md`.
4. Resolve or waive each BLOCKER in ticket `Decision Log`.

Optional: `scripts/architect/run_cold_critic.sh` (helper).

## Research

Launch parallel read-only subagents (official docs, GitHub, repo ADRs, web). Max 3 rounds. See `references/researcher-protocol.md`.

## Bugfix helper

Scope + non-goals required. Propose 2–3 approaches with tests/edge cases; no code edits. Hand off to `/developer-skill`.

## Validate

Pre-dev gate: AC quality, Gherkin gaps, risks, ADR fit. FAIL blocks Ready without human waiver.

## References

- `references/skeptical-reviewer.md`
- `references/researcher-protocol.md`
- `references/bugfix-helper.md`
- `references/plan-validator.md`
- `config.yaml`
- `docs/guides/agentic-team-operating-model.md`
