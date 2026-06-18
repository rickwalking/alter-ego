# AE-0219 — Harden the external cross-LLM review runner

Status: Intake
Tier: T1
Priority: Medium
Type: Quality
Area: Agent Workflow
Owner: Agent
Agent Lane: developer → qa
Branch: TBD
Kanban Card: AE-0219
Created: 2026-06-18
Updated: 2026-06-18
Source: kaizen session-2026-06-18 (K4, class L4) — `.agent/reports/kaizen-session-2026-06-18.plan.md`

## Goal

Make external cross-LLM review (architect skeptical / kaizen external pass)
robust to dead models and hallucinated reviews, so a fragile or off-topic review
is never silently trusted.

## Problem

During AE-0216 the external review was fragile: `gemini-3-pro-preview` 404'd
(decommissioned), `gemini-2.5-pro` **hallucinated** (reviewed "aider" instead of
the actual subject), and opencode's hosted provider was out of balance — only one
model worked. A hallucinated review that passes silently is worse than no review.

## Scope

- Document a **provider fallback order** in the architect/kaizen external-review
  runbook (`references/external-qa.md` and/or `scripts/qa/run_external_qa.sh`).
  Approved fallback chain (user-specified 2026-06-18):
  1. **codex** with `gpt-5.5`
  2. **opencode** with `kimi-k2.7`
  3. **opencode** with `glm-5.2`
  4. **opencode** with `mimo-2.5-pro`
- Add a cheap **engagement sanity check**: the review must reference the actual
  subject (real filenames / ticket id / symbols from the diff). A review that
  fails the check is **discarded**, not trusted, and the runner falls through to
  the next provider.

## Non-Goals

- Any gate/threshold change (ratchet HOLD — process/doc + runner robustness only).

## Classification (AE-0153 / AE-0180)

- Quality/tooling. The sanity check ships with a **seeded-violation test**: a
  fabricated review that mentions no real subject token must be rejected by the
  check (and a genuine one accepted).

## Acceptance Criteria

- [ ] Provider fallback order documented in the external-review runbook with the
      approved chain (codex/gpt-5.5 → opencode/kimi-k2.7 → glm-5.2 → mimo-2.5-pro).
- [ ] Engagement sanity check implemented: a review not referencing real
      subject tokens (filenames/ticket/symbols) is rejected and the runner
      advances to the next provider.
- [ ] **Seeded-violation test**: a fabricated off-topic review FAILS the sanity
      check; a genuine on-topic review PASSES.
- [ ] mypy + ruff clean (for any script changes).

## References

- Kaizen plan: `.agent/reports/kaizen-session-2026-06-18.plan.md` (K4)
- `scripts/qa/run_external_qa.sh`, `skills/delivery/qa-agent/references/external-qa.md`
