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
Updated: 2026-06-25
Source: kaizen session-2026-06-18 (K4, class L4) — `.agent/reports/kaizen-session-2026-06-18.plan.md`;
strengthened by kaizen session-2026-06-25 (P3, class C4) — `.agent/reports/kaizen-session-2026-06-25.plan.md`

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

- **Fix the actual hardcoded default (kaizen 2026-06-25, P3).** Doc-only is
  insufficient: `scripts/qa/run_external_qa.sh:21` and
  `scripts/kaizen/run_external_kaizen.sh:25` hardcode `TOOL="${3:-opencode}"`,
  and `ext_pick_tool` (`scripts/lib/external_agent.sh:32-40`) falls back on tool
  *installation* only — not balance. So `opencode` (out of balance) is still
  selected first and the run fails mid-stream with "Insufficient balance". This
  friction recurred in sessions 2026-06-22 / -24 / -25 AFTER this ticket was
  filed doc-only. Change the runner default to the approved chain head
  (**codex / gpt-5.5**).
- **Add a fail-fast preflight balance/reachability probe** in
  `scripts/lib/external_agent.sh`: before committing to a provider, detect
  "Insufficient balance" / provider-unreachable and AUTO-ADVANCE to the next
  entry in the chain, surfacing a clear one-line message — instead of failing
  ~mid-run after the session has started. (Today the only post-launch check is a
  `stream providerID` hang-detector, not a balance check.)
- Document the **provider fallback order** in the architect/kaizen external-review
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

- [ ] The runner DEFAULT is the approved chain head (codex/gpt-5.5), not
      `opencode` — `run_external_qa.sh` + `run_external_kaizen.sh` updated.
- [ ] A preflight balance/reachability probe detects "Insufficient balance" /
      unreachable provider and auto-advances to the next chain entry with a clear
      message, BEFORE the review session proceeds — not a mid-run failure.
- [ ] Provider fallback order documented in the external-review runbook with the
      approved chain (codex/gpt-5.5 → opencode/kimi-k2.7 → glm-5.2 → mimo-2.5-pro).
- [ ] Engagement sanity check implemented: a review not referencing real
      subject tokens (filenames/ticket/symbols) is rejected and the runner
      advances to the next provider.
- [ ] **Seeded-violation test**: a fabricated off-topic review FAILS the sanity
      check; a genuine on-topic review PASSES.
- [ ] mypy + ruff clean (for any script changes).

## Notes (kaizen 2026-06-25)

- Coordinate with **AE-0281** (external-run commit lock) — both edit
  `scripts/lib/external_agent.sh`; sequence to avoid conflicting changes.

## References

- Kaizen plans: `.agent/reports/kaizen-session-2026-06-18.plan.md` (K4),
  `.agent/reports/kaizen-session-2026-06-25.plan.md` (P3, class C4)
- `scripts/qa/run_external_qa.sh`, `scripts/kaizen/run_external_kaizen.sh`,
  `scripts/lib/external_agent.sh`,
  `skills/delivery/qa-agent/references/external-qa.md`
