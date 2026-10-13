# AE-0348 — GrokBot Autopilot epic (viral AI themes → carousel → Telegram approval → Instagram)

Status: Ready
Tier: T3
Priority: High
Type: Epic
Area: Cross-cutting
Owner: Grok (Cursor CLI, grok-4.7-high)
Agent Lane: planner → architect → developer → qa → release
Branch: TBD (one branch per child)
Kanban Card: TBD
Created: 2026-10-13
Updated: 2026-10-13

## Goal

A daily bot finds viral AI themes (X via web search + free sources), ranks them with Grok (Cursor CLI `grok-4.7-high`), generates a carousel through the existing editorial workflow, sends it to the owner on Telegram for Approve / Rework / Reject, and publishes to Instagram **only** after explicit owner approval. Zero new subscriptions. Architecture: [docs/architecture/grokbot-autopilot.md](../../docs/architecture/grokbot-autopilot.md), ADR-0020.

## Problem

There is no trend discovery, no unattended workflow mode (6 human gates), no machine auth (JWT 60 min, no refresh), no outbound notification channel, and Instagram publishing is non-idempotent and unconfigured in prod. Publishing a carousel today takes ~6 manual approvals plus a manual publish.

## Scope

- Coordinate AE-0349 through AE-0360 in dependency order.
- Wave A (foundation): AE-0349 spike, AE-0350 module + migration, AE-0351 service API key.
- Wave B (inputs + engine): AE-0352 collectors, AE-0353 topic intake, AE-0354 runner + gate policy.
- Wave C (human loop + output): AE-0355 Telegram notifier, AE-0356 Telegram webhook, AE-0357 idempotent IG publish, AE-0358 IG token store/refresher.
- Wave D (ship): AE-0359 prod wiring, AE-0360 ops scout (Cursor CLI on droplet).

## Non-Goals

- Paid X API / xAI `x_search`; xcancel/Nitter mirrors as a dependency (xcancel returned HTTP 451 on 2026-10-13).
- Publishing without an owner Telegram approval.
- LinkedIn API publishing, scheduling slots, multi-account support.
- Giving the LLM (Grok) network credentials or API access.

## Acceptance Criteria

- [ ] WHEN the daily scout timer fires THE SYSTEM SHALL create at most `AUTOPILOT_DAILY_CAP` carousels from ranked, deduped topics whose sources all appear in the collected signals.
- [ ] WHEN a carousel reaches `final_review` THE SYSTEM SHALL send the slides + caption to the owner on Telegram with Approve / Rework / Reject buttons.
- [ ] WHEN the owner taps Approve THE SYSTEM SHALL publish exactly once to Instagram and reply with the permalink.
- [ ] WHEN the owner taps Rework THE SYSTEM SHALL re-run the chosen phase with the owner's free-text feedback and re-notify.
- [ ] WHEN any step fails THE SYSTEM SHALL end in a terminal or escalated state and notify the owner on Telegram (never silently stuck).
- [ ] WHEN all children are Done THE end-to-end smoke (scout → Telegram → approve → IG post) SHALL be recorded in Test Evidence.

## Gherkin Scenarios

```gherkin
Feature: GrokBot autopilot end-to-end

  Scenario: Happy path from viral theme to Instagram post
    Given the scout collected signals and Grok ranked a topic
    When the autopilot generates the carousel and the owner taps Approve on Telegram
    Then the carousel is published once to Instagram and the owner receives the permalink

  Scenario: Owner rejects
    Given a carousel is awaiting the owner
    When the owner taps Reject
    Then nothing is published and the carousel stays private
```

## Delta

### ADDED

- Epic tracking AE-0349..AE-0360.

### MODIFIED

- None.

### REMOVED

- None.

## Affected Areas

- Backend: new `modules/autopilot`
- Database: 4 tables
- API: `/api/autopilot/*`, `/api/telegram/webhook`, IG status route
- Deployment: secrets, Cloudflare rule, systemd units
- Docs: architecture doc + ADR-0020

## Dependencies

- Blocks: none
- Blocked by: none
- Related: ADR-0020, ADR-0004 (outbox), ADR-0009 (modular monolith), ADR-0011

## Implementation Plan

1. Wave A → B → C → D as listed in Scope; each child is its own branch + PR.
2. Do not merge any wave to `main` mid-incident; `main` auto-deploys prod.
3. Run the E2E smoke after AE-0359 + AE-0360 are deployed.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-10-13 00:00

Ticket created from docs/architecture/grokbot-autopilot.md (ticket #epic).

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Decision Log

ADR-0020 (proposed): read-only LLM scout on host + deterministic in-backend autopilot + Telegram-gated Instagram publish. X via `ddgs` `site:x.com` snippets; mirror resolver off by default.

## Blockers

None.

## Final Summary

Pending.
