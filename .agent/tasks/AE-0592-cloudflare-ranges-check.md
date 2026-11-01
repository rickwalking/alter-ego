# AE-0592 — Periodic check that nginx's Cloudflare ranges are current

Status: Intake
Tier: T1
Priority: Low
Type: Chore
Area: Deployment
Owner: Pedro
Agent Lane: developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-11-01
Updated: 2026-11-01

## Goal

Know when Cloudflare publishes new edge ranges, so the `set_real_ip_from` list in nginx stays complete.

## Problem

AE-0589 pins Cloudflare's published ranges (<https://www.cloudflare.com/ips/>, checked 2026-11-01) in
`nginx/nginx.conf.ssl` and `nginx/nginx.conf`. nginx trusts `CF-Connecting-IP` only from those ranges. If Cloudflare
adds a range, visitors served from it fall back to the edge address for the rate limits (the state before AE-0589,
not a security hole), and nobody notices. The update step is documented in `docs/deployment/DEPLOYMENT_GUIDE.md`,
but nothing reminds anyone to run it.

## Scope

- A scheduled CI job (weekly) that fetches <https://www.cloudflare.com/ips-v4> and `/ips-v6` and compares them with
  the `set_real_ip_from` lines in both nginx configs; it fails (or opens an issue, per Pedro's preference) when they
  differ, listing the added and removed ranges.
- A test that the comparison fires on a seeded difference (rule-fires standard).

## Non-Goals

- Fetching the ranges at deploy time or at nginx start (a Cloudflare outage must not break a deploy).
- Changing the rate limits or the trust rules from AE-0589.

## Acceptance Criteria

- [ ] AC1 The job passes when both configs match Cloudflare's published lists.
- [ ] AC2 The job reports the added and removed ranges when they differ.
- [ ] AC3 A seeded difference makes the check fail in a unit test.

## Gherkin Scenarios

```gherkin
Feature: Cloudflare ranges in nginx stay current

  Scenario: The pinned ranges match Cloudflare's lists
    Given both nginx configs list exactly Cloudflare's published ranges
    When the weekly check runs
    Then it passes

  Scenario: Cloudflare adds a range
    Given Cloudflare publishes a range that the nginx configs do not list
    When the weekly check runs
    Then it fails and names the missing range
```

## Delta

### ADDED

- Weekly workflow and a small comparison script with its test.

### MODIFIED

- None.

### REMOVED

- None.

## Affected Areas

- Backend: none
- Frontend: none
- Database: none
- API: none
- Tests: comparison script test
- Docs: DEPLOYMENT_GUIDE update step references the job
- Prompts/LLM: none
- Observability: none
- Deployment: new scheduled workflow (read-only, no deploy)

## Dependencies

- Blocks: none
- Blocked by: AE-0589
- Related: AE-0589

## Implementation Plan

1. Script: parse `set_real_ip_from` from both configs, fetch the two lists, diff.
2. Seeded-difference unit test.
3. Weekly `schedule` workflow running the script.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-11-01 13:40

Ticket filed with AE-0589 at Pedro's request (2026-11-01): the ranges are a pinned list, so a periodic check is
needed.

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Decision Log

Pending.

## Blockers

None.

## Final Summary

Pending.
