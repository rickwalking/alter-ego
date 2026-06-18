# AE-0220 — Serialize prod deploys with a concurrency group in deploy.yml

Status: Dev Complete
Tier: T1
Priority: High
Type: Quality
Area: CI/DevOps
Owner: Agent
Branch: feat/dev-wave-ae0220-0227
Created: 2026-06-18
Updated: 2026-06-18
Source: kaizen session-2026-06-18b (P1, class FC4) — `.agent/reports/kaizen-session-2026-06-18b.plan.md`

## Goal

Prevent two `deploy.yml` runs from executing concurrently against the same
production droplet, so merges to `main` queue safely instead of racing.

## Problem

`.github/workflows/deploy.yml` triggers on `push` to `main` and has **no
`concurrency:` control** (verified: `grep concurrency .github/workflows/deploy.yml`
→ no match). In the AE-0216 session, two PRs (#52, #53) were merged ~30s apart and
spawned **two concurrent deploy runs** on the same DigitalOcean droplet. Both
succeeded by luck, but concurrent deploys can race: interleaved `.env` rewrites
(deploy rewrites the server `.env` from GitHub Secrets every run), a half-applied
image swap, or overlapping migration steps — the same blast radius behind AE-0207.

## Scope

- Add a top-level `concurrency:` block to `.github/workflows/deploy.yml`:
  ```yaml
  concurrency:
    group: prod-deploy
    cancel-in-progress: false
  ```
- `cancel-in-progress: false` (queue, do **not** cancel): a deploy that has begun
  mutating the droplet must finish; the next deploy runs after it.

## Non-Goals

- Do not refactor unrelated code
- Changing what the deploy does (image build, `.env` rewrite, migration gating)
- Touching AE-0207's migrate-on-deploy switch (stays OFF, unrelated)

## Acceptance Criteria

- [x] `deploy.yml` has a top-level `concurrency: { group: prod-deploy, cancel-in-progress: false }`.
- [x] The workflow still parses (PyYAML safe_load OK; `concurrency` block asserted; actionlint not installed locally, CI will lint).
- [x] Decision Log documents the `cancel-in-progress: false` choice (queue, never
      cancel an in-flight prod deploy).
- [x] No other `deploy.yml` behavior changed (diff is the concurrency block + its comment only).

## Decision Log

- **cancel-in-progress: false (queue, do not cancel).** A prod deploy that has
  begun mutating the droplet (server `.env` rewrite from Secrets + image swap)
  must run to completion; cancelling mid-flight could leave a half-applied state.
  Queuing the next run behind it is the safe single-flight behavior.

## Classification (AE-0153 / AE-0180)

CI/config change with **no public/user-visible application behavior change** — per
AE-0153 no `.feature` required; per AE-0180 no static-analysis rule added, so no
rule-fires test applies. Proven by the workflow key present + workflow still parses.

## Repro Steps

1. Merge two PRs to `main` within ~30s.
2. Observe two simultaneous `deploy.yml` runs in `gh run list --workflow=deploy.yml`.

## Affected Areas

- [ ] Backend
- [ ] Frontend
- [ ] Tests

## Dependencies

None.

## Progress Log

### 2026-06-18

Ticket created from kaizen session-2026-06-18b (P1).

### 2026-06-18 — Dev Complete

Added the `concurrency` block (group `prod-deploy`, `cancel-in-progress: false`)
after the `on:` triggers in `deploy.yml`. Verified the workflow still parses.

## Files Touched

- `.github/workflows/deploy.yml` — added top-level `concurrency` block + comment.

## Test Evidence

```
$ python3 -c "import yaml; d=yaml.safe_load(open('.github/workflows/deploy.yml')); print(d['concurrency'])"
{'group': 'prod-deploy', 'cancel-in-progress': False}
```
actionlint is not installed locally; the GitHub Actions runner validates the
workflow on push. No other keys changed (diff is the concurrency block only).

## QA Report

Pending.

## Blockers

None.

## References

- Kaizen plan: `.agent/reports/kaizen-session-2026-06-18b.plan.md` (P1)
- Landmine: `.agent/handoff/learnings-log.jsonl` 2026-06-18T19:14 — "two merges within ~30s ran two concurrent deploy.yml runs"
- Memory: `do-droplet-prod-deploy` (deploy rewrites server `.env` from Secrets every run)
