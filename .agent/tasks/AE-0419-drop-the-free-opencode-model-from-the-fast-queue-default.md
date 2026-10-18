# AE-0419 — Drop the free OpenCode model from the fast-queue default

Status: In Development
Tier: T1
Priority: High
Type: Bug
Area: DevOps
Owner: Claude (orchestrator)
Branch: fix/ae-0419-drop-free-opencode-model
Created: 2026-10-17
Updated: 2026-10-17

## Goal

The prod fast model queue never starts with `opencode/deepseek-v4.1-flash-free`, including on a
deploy without the `LLM_MODEL_QUEUE_FAST` repo variable.

## Problem

Since 2026-10-17 every call to the free model through the OpenCode sidecar fails with
`FreeTierError: OpenCode's free tier can only be used from within OpenCode`, and its breaker opens
for 6 h (Telegram alert). Investigation (2026-10-17):

- On the droplet, `opencode run -m opencode/deepseek-v4.1-flash-free` fails the same way from
  OpenCode's own CLI, both signed in and with a signed-out profile (OpenCode 1.18.35).
- The same command answers `OK` from a residential connection with 1.18.35 and with the latest
  1.19.3, signed out.
- So OpenCode refuses its free tier from server IPs. That is the provider's policy for automated
  use; prod will not route around it (no proxying through a home connection).

The orchestrator already set the repo variable `LLM_MODEL_QUEUE_FAST=go:deepseek-v4.1-flash,go:qwen3.8-flash`
and the server `.env`, but `deploy.yml`'s fallback default still starts with the free model.

## Scope

- `deploy.yml`: fallback default `go:deepseek-v4.1-flash,go:qwen3.8-flash`, with the reason.
- `docs/backend/llm-model-routing.md`: prod queue and the AE-0419 note on the sidecar.

## Non-Goals

- Removing the sidecar service or the `sidecar:` queue support (still usable for a provider that
  allows server use).
- Code changes: none.

## Acceptance Criteria

- [x] `deploy.yml` default fast queue has no free sidecar model.
- [x] The routing doc states the prod queue and why the free model is out.
- [x] No public/user-visible behavior change beyond what prod already runs (the repo variable and
      server `.env` already hold this queue); config/doc-only ticket, no `.feature` (CLAUDE.md
      AE-0153 config path). No static-analysis rule is added, so no seeded-violation test applies.
- [x] Affected gates: agent ticket hygiene, CI gate (workflow + docs paths).

## Repro Steps

1. On the droplet: `docker exec alter-ego-opencode-1 opencode run -m opencode/deepseek-v4.1-flash-free "hi"`.
2. Result: `FreeTierError`.

## Affected Areas

- [ ] Backend
- [ ] Frontend
- [ ] Tests
- [x] Deployment / docs

## Dependencies

None.

## Progress Log

### 2026-10-17 23:40

Ticket created; default and doc updated.

## Files Touched

- .github/workflows/deploy.yml
- docs/backend/llm-model-routing.md

## Test Evidence

Config/doc only. Prod verification: backend env `LLM_MODEL_QUEUE_FAST=go:deepseek-v4.1-flash,go:qwen3.8-flash` since 14:08Z; carousels generated and published on it afterwards.

## QA Report

Reviewer sign-off on the no-`.feature` classification: config-only (orchestrator).

## Blockers

None.
