# AE-0359 — Prod wiring: secrets in deploy.yml + compose, Cloudflare skip rule, Telegram setWebhook

Status: Ready
Tier: T2
Priority: High
Type: Chore
Area: deployment
Owner: Grok (Cursor CLI, grok-4.7-high)
Agent Lane: developer (Grok for code; Pedro for GitHub Secrets + Cloudflare) → qa → release
Branch: feat/ae-0359-autopilot-prod-wiring
Kanban Card: TBD
Created: 2026-10-13
Updated: 2026-10-13
Parent: AE-0348

## Goal

Make the autopilot actually runnable in production.

## Problem

`META_IG_ACCESS_TOKEN`, `META_IG_USER_ID`, `CAROUSEL_PUBLIC_BASE_URL` are absent from `docker-compose.prod.yml:60-82` and `.github/workflows/deploy.yml:126-148`; the new Telegram/API-key/encryption settings are absent too; Cloudflare may bot-challenge Meta's image fetcher.

## Scope

- Add to `deploy.yml` env generation + `docker-compose.prod.yml` backend `environment:`: `META_IG_ACCESS_TOKEN`, `META_IG_USER_ID`, `CAROUSEL_PUBLIC_BASE_URL=https://marinssolutions.com`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_OWNER_CHAT_ID`, `TELEGRAM_WEBHOOK_SECRET`, `GROKBOT_API_KEY_SHA256`, `CREDENTIALS_ENCRYPTION_KEY`, `AUTOPILOT_ENABLED` (default false), `AUTOPILOT_OWNER_USER_ID`, `AUTOPILOT_DAILY_CAP`.
- Extend the existing env-completeness check (if any under `scripts/ci/`) so a missing autopilot var in compose vs deploy.yml fails CI; add the seeded-violation test (AE-0180).
- Pedro (manual): add GitHub Secrets; Cloudflare WAF custom rule 'Skip' for path `/api/carousels/*/slide-images/*` (bot fight / challenges); verify `curl -A 'facebookexternalhit/1.1' -I https://marinssolutions.com/api/carousels/<public-id>/slide-images/pt/slide_1.jpg` → 200 `image/jpeg`.
- After deploy: run `set_webhook` script inside the backend container; `getWebhookInfo` shows the URL and no last_error.
- Rollout: deploy with `AUTOPILOT_ENABLED=false`, verify, then flip to true.

## Non-Goals

- Code changes to features (done in earlier tickets).

## Acceptance Criteria

- [ ] WHEN deploy.yml and compose disagree on an autopilot variable THE CI gate SHALL fail (seeded-violation test proves it).
- [ ] WHEN Meta's user agent fetches a public slide THE edge SHALL return 200 image/jpeg (evidence pasted).
- [ ] WHEN `getWebhookInfo` is called after deploy THE webhook URL SHALL be set with no `last_error_message`.
- [ ] WHEN deployed with `AUTOPILOT_ENABLED=false` THE worker SHALL not run the autopilot.

## Gherkin Scenarios

Not required — CI/config/deployment ticket. No public/user-visible behavior change by itself (features gated by AUTOPILOT_ENABLED=false). Seeded-violation test for the env-parity gate; affected gates: backend + ci scripts. Needs QA sign-off on this classification (AE-0153).

## Delta

### ADDED

- Env-parity check + seeded-violation test (if not existing)

### MODIFIED

- `.github/workflows/deploy.yml`
- `docker-compose.prod.yml`
- `backend/.env.example`

### REMOVED

- None.

## Affected Areas

- Deployment
- CI
- Cloudflare (manual)

## Dependencies

- Blocks: AE-0360 go-live
- Blocked by: AE-0349, AE-0356, AE-0357, AE-0358

## Implementation Plan

1. Grok: compose + deploy.yml + env-parity gate + test.
2. Pedro: secrets + Cloudflare rule.
3. Merge only when ready for a live deploy (main auto-deploys); single Alembic head check.
4. Post-deploy verification commands.

## Implementer Notes (read first — Cursor CLI / Grok)

- Source of truth: [docs/architecture/grokbot-autopilot.md](../../docs/architecture/grokbot-autopilot.md) and [ADR-0020](../../docs/decisions/0020-grokbot-autopilot.md). If this ticket and the doc disagree, STOP and ask — do not guess.
- Read `CLAUDE.md`, `backend/CLAUDE.md`, `backend/AGENTS.md`, `docs/architecture/module-conventions.md` before coding.
- Module rules: new code lives in `backend/src/rag_backend/modules/autopilot/` following `modules/_template/` (domain/application/infrastructure/api + `public.py` + `bootstrap.py` + `constants.py`). Other modules are reached ONLY through their `public.py`; add an import-linter contract for `autopilot` (module-conventions §7a/§7d).
- Hard rules: no magic strings (constants.py), no `Any`/`object`, ≤3 args per function (Pydantic/typed command objects), guard clauses, ≤400 lines/file, mypy strict, ruff clean, 90%+ branch coverage.
- Behavior-changing tickets: write the `.feature` file FIRST under `backend/tests/features/` and reference scenario names in test comments.
- Never commit secrets. Never push `main` (auto-deploys prod). Branch per ticket, lowercase conventional commits.
- Done = `bash scripts/ci/gate-capture.sh backend` green with the `GATES_JSON:` line pasted in the dev summary + `/qa-agent` PASS. Never pipe gates to `tail`/`head`.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked
- [ ] No secret values in repo
- [ ] Single Alembic head before merge

## Progress Log

### 2026-10-13 00:00

Ticket created from docs/architecture/grokbot-autopilot.md (ticket #10).

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Decision Log

See ADR-0020.

## Blockers

Manual steps (GitHub Secrets, Cloudflare) require Pedro.

## Final Summary

Pending.
