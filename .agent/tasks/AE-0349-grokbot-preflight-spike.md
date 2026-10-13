# AE-0349 — GrokBot pre-flight spike: Cursor CLI + Grok on droplet, Telegram bot, Instagram token

Status: Ready
Tier: T2
Priority: Critical
Type: Spike
Area: ops
Owner: Grok (Cursor CLI, grok-4.7-high)
Agent Lane: developer (owner: Pedro, manual)
Branch: feat/ae-0349-grokbot-preflight-spike
Kanban Card: TBD
Created: 2026-10-13
Updated: 2026-10-13
Parent: AE-0348

## Goal

Prove every external dependency works before code is written: Cursor CLI headless with `grok-4.7-high` on the droplet, a Telegram bot + owner chat id, and an Instagram Business/Creator long-lived token that can call the content-publishing endpoints.

## Problem

Cursor moved to 'The X Subscription' on 2026-10-12; whether the current plan covers headless CLI use is unverified. Instagram publishing needs a professional account + token that does not exist in prod. Building before verifying risks a dead end.

## Scope

- Install Cursor CLI on the droplet under a dedicated `grokbot` user; `agent status`; `agent --list-models | grep -i grok`; one `timeout 120 agent -p --model grok-4.7-high --output-format json 'reply with {"ok":true}'`.
- Record the exact model id that works (expect `grok-4.7-high`; fallback `grok-4.6-high`). Set Cursor on-demand spend cap to $0.
- Create Telegram bot via BotFather; get owner `chat_id` (send /start, read `getUpdates`).
- Confirm the Instagram account is Business or Creator; create a Meta app with 'Instagram API with Instagram Login'; generate a long-lived token with `instagram_business_basic` + `instagram_business_content_publish`; `GET graph.instagram.com/me?fields=user_id,username` and `GET /<IG_ID>/content_publishing_limit` succeed.
- Check Page Publishing Authorization if the IG account is linked to a Facebook Page.

## Non-Goals

- Writing application code.
- Committing any secret (record secrets only in a password manager / GitHub Secrets).

## Acceptance Criteria

- [ ] WHEN `agent -p --model <id>` runs headless on the droplet THE command SHALL return JSON with a `result` field within 120 s (model id recorded in Decision Log).
- [ ] WHEN `getUpdates` is called after /start THE owner chat id SHALL be recorded (as a GitHub Secret name, not value).
- [ ] WHEN `content_publishing_limit` is queried with the new token THE API SHALL return 200 (token expiry date recorded).
- [ ] WHEN any check fails THE ticket SHALL be Blocked with the error, and the epic paused.

## Gherkin Scenarios

Not required — manual spike, no product behavior change. Evidence = command outputs (redacted) in Test Evidence.

## Delta

### ADDED

- Decision Log entries: working model id, IG account type, token expiry date.

### MODIFIED

- None.

### REMOVED

- None.

## Affected Areas

- Deployment: droplet user `grokbot`, Cursor CLI install
- Docs: Decision Log only

## Dependencies

- Blocks: AE-0359, AE-0360
- Blocked by: none
- Related: AE-0348

## Implementation Plan

1. Droplet: `adduser --disabled-password grokbot`; install Cursor CLI as that user; login with `CURSOR_API_KEY` from `/etc/grokbot/env` (mode 600).
2. Run the CLI checks; paste redacted output.
3. BotFather → token; `/start`; `curl https://api.telegram.org/bot$T/getUpdates`.
4. Meta app dashboard → Instagram → API setup → Generate token; run the two Graph calls.
5. Store values as GitHub Secrets: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_OWNER_CHAT_ID`, `META_IG_ACCESS_TOKEN`, `META_IG_USER_ID`.

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
- [ ] No secret values pasted in the ticket

## Progress Log

### 2026-10-13 00:00

Ticket created from docs/architecture/grokbot-autopilot.md (ticket #0).

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Decision Log

- 2026-10-13 Cursor CLI: logged in locally, `agent --list-models` lists `grok-4.7-high`; headless run confirmed (model reported "Grok 4.7 256K High"). Uses the existing Cursor subscription Grok limits. Droplet install still pending (AE-0360).
- 2026-10-13 Telegram: bot `@carousel_creator_bot` verified via `getMe`. Owner chat id `880041173` (private chat, from `/start`; test message delivered) = `TELEGRAM_OWNER_CHAT_ID`. Token was shared in a chat transcript; owner decided not to revoke. Store it only as GitHub Secret `TELEGRAM_BOT_TOKEN` (never in the repo).
- 2026-10-13 Instagram: Meta app `alter-ego-publisher` (Development mode, use case "Manage messaging & content on Instagram", Instagram Login). `/me` → `username=pedromarins.ai`, `account_type=MEDIA_CREATOR`, `user_id=17841480011497925` (= `META_IG_USER_ID`). Token is an Instagram-Login token → requires `graph.instagram.com` (see AE-0357 host fix).
- 2026-10-13 `GET /17841480011497925/content_publishing_limit` → `quota_usage=0`, `quota_total=100`, `quota_duration=86400` → publish permission confirmed.
- Pre-flight complete except droplet Cursor CLI install (moved to AE-0360 install step).

## Blockers

None.

## Final Summary

Pending.
