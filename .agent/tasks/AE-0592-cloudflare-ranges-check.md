# AE-0592 — Periodic check that nginx's Cloudflare ranges are current

Status: Dev Complete
Tier: T1
Priority: Low
Type: Chore
Area: Deployment
Owner: Pedro
Agent Lane: developer → qa → release
Branch: chore/ae-0592-cloudflare-ranges-check
Kanban Card: TBD
Created: 2026-11-01
Updated: 2026-11-02

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
  the `set_real_ip_from` lines in both nginx configs; it fails when they differ, listing the added and removed
  ranges in the job log and the step summary (no issue, no post; see Decision Log).
- A test that the comparison fires on a seeded difference (rule-fires standard).

## Non-Goals

- Fetching the ranges at deploy time or at nginx start (a Cloudflare outage must not break a deploy).
- Changing the rate limits or the trust rules from AE-0589.

## Acceptance Criteria

- [x] AC1 The job passes when both configs match Cloudflare's published lists.
- [x] AC2 The job reports the added and removed ranges when they differ.
- [x] AC3 A seeded difference makes the check fail in a unit test.

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

### 2026-11-02

Implemented on `chore/ae-0592-cloudflare-ranges-check`: checker script, rule-fires tests, weekly workflow, guide
update. Gates covering the touched files green (dev summary).

## Files Touched

- `scripts/ci/check_cloudflare_ranges.py` (new, stdlib only)
- `backend/tests/unit/scripts_ci/test_check_cloudflare_ranges.py` (new)
- `.github/workflows/cloudflare-ranges.yml` (new, weekly + `workflow_dispatch`, `contents: read`)
- `docs/deployment/DEPLOYMENT_GUIDE.md` (update step points at the job)

## Test Evidence

- `backend/tests/unit/scripts_ci/test_check_cloudflare_ranges.py`: 13 passed (no network; local files or a stub
  HTTPS connection). Seeded differences exit 1, fetch/parse failures exit 2.
- Live run 2026-11-02: `Cloudflare ranges OK: 22 ranges match in 2 configs`, exit 0.
- Per-gate runs and actionlint: `.agent/reports/AE-0592.dev-summary.md`.

## QA Report

Pending.

## Decision Log

- 2026-11-02 — On a difference the job FAILS and lists the added and removed ranges per config in the job log and
  `$GITHUB_STEP_SUMMARY`. It does not open a GitHub issue or post anywhere (fixed in the worker brief; keeps the job
  `contents: read` with no write token). A red scheduled run notifies through GitHub's normal failed-workflow email.
- 2026-11-02 — Exit codes: 0 match, 1 difference, 2 check could not run (fetch error, HTTP error, empty list, a body
  that is not a list of ranges such as an HTML error page, or an unreadable config). Exit 2 says "this is NOT a pass",
  so a fetch failure is never reported as "ranges match".
- 2026-11-02 — Ranges are compared as networks (`ipaddress.ip_network(strict=False)`), so notation (case, host bits)
  is not drift; each config is diffed on its own so the report names the file that is off.
- 2026-11-02 — The checker lives in `scripts/ci/` so changes to it trigger the backend gate workflow (path filter),
  which runs its test.
- 2026-11-02 — Schedule: Mondays 06:00 UTC (after the 04:00 mutation run).
- 2026-11-02 — The fetch uses `http.client.HTTPSConnection` to the fixed host `www.cloudflare.com` (HTTPS only, no
  scheme taken from input) instead of `urllib.request.urlopen`, so no `noqa`/`nosec` suppression is needed; a non-200
  answer is a fetch failure (exit 2).
- 2026-11-02 — Classification: CI/config/tooling, "unit tests suffice" (root CLAUDE.md, AE-0153). No `.feature`:
  (a) no public/user-visible behavior change: no app, API, nginx or deploy change; the job is read-only and does not
  run at deploy time; (b) seeded-violation tests: `test_fires_when_cloudflare_adds_a_range`,
  `test_fires_when_cloudflare_retires_a_range`, `test_fires_when_only_one_config_drifts`,
  `test_config_without_ranges_differs` (exit 1) plus the fetch/parse failure tests (exit 2); the ticket's two
  Gherkin scenarios are named in the test docstrings; (c) affected gates: backend format, lint, lint-diff,
  strict-diff, type, comments, gherkin-refs, integrity, duplication, bandit, test (via the `scripts/ci/**` path
  filter); the new scheduled workflow itself; (d) reviewer/QA sign-off on the no-`.feature` classification is
  requested on the PR.
- 2026-11-03 — Lead review sign-off on the no-`.feature` classification: agreed. The change adds a read-only,
  scheduled drift check and its tests; nothing user-visible, no API, nginx or deploy path changes. The seeded
  drift tests prove the check fires (exit 1) and the fetch/parse tests prove it fails loudly (exit 2).
- 2026-11-02 — Local proof is the per-gate runs covering the touched files (worker brief; the Pi is shared and a full
  backend suite was already running from another session). CI runs the full backend gate set on the PR.

## Blockers

None.

## Final Summary

Pending.
