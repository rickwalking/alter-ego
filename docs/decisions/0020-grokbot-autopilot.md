---
status: proposed
date: 2026-10-13
decision-makers: Pedro Marins
consulted: Claude (architecture research)
informed: delivery team
---

# ADR-0020: GrokBot autopilot: LLM scout outside the app, deterministic autopilot inside, human-gated Instagram publish

## Context and Problem Statement

We want a bot that does three things:

1. Finds viral AI themes.
2. Generates carousels through the existing editorial workflow.
3. Asks the owner to approve before auto-publishing to Instagram.

It must not add any subscription. The scouting LLM must be Grok through Cursor CLI.

The codebase has several gaps today:

- **Auth:** there is no machine auth (JWT only, 60 min, no refresh).
- **Workflow:** there is no auto mode (six `interrupt()` gates), and `workflow/start` is synchronous, about 68 s, behind a ~100 s Cloudflare cap.
- **Notifications:** there are no outbound notifications.
- **Instagram:** publishing is not idempotent, and the prod config is missing.

Full analysis: [grokbot-autopilot.md](../architecture/grokbot-autopilot.md).

## Decision Drivers

- No new subscriptions. Use only free APIs and the existing droplet and Cursor plan.
- Nothing is ever published without an explicit owner approval.
- Scraped content and LLM output are untrusted, so contain prompt injection.
- Never double-post. Never leave a run stuck.

## Considered Options

1. **External bot drives the public HTTP API** (log in as a user, 6× resume, poll state).
2. **Cursor Grok Bot / agent with API credentials and tools** (MCP) does everything.
3. **Split: a read-only LLM scout on the host, plus a deterministic `autopilot` module in the backend, plus Telegram approval.**

## Decision Outcome

Chosen: **Option 3**.

- **Grok's job:** through `agent -p --model grok-4.7-high`, sandboxed and without secrets, Grok only ranks pre-fetched free signals into schema-validated topic JSON.
- **The backend's job:** it drives the workflow in-process. It auto-approves intermediate gates only when deterministic checks pass, and it always stops at `final_review`. It notifies the owner on Telegram, and it publishes to Instagram through an idempotent outbox job, only on an allowlisted owner callback.

### Consequences

- Good, because the LLM can never publish or touch credentials.
- Good, because the in-process runner avoids the JWT-expiry, `lock_version`-race and Cloudflare-timeout failure modes.
- Good, because Telegram, the Instagram Graph API (own account), HN, HF, RSS and Bluesky are all free.
- Bad, because it adds a bounded context (`modules/autopilot`), four tables and host-level systemd units to operate.
- Bad, because X signals come only from search-engine snippets (`ddgs` `site:x.com`), with no like or repost counts. Official X paths are pay-per-use, and the xcancel mirror returned HTTP 451 (suspended over legal proceedings) on 2026-10-13. A mirror resolver exists only as an off-by-default port.
- Neutral, because per-carousel provider spend still exists. A daily cap bounds it.

## Rejected

- **Option 1:** it needs a user password on a bot, re-login every hour, and six racy HTTP calls, and it hits the 100 s start timeout.
- **Option 2:** it gives an injectable LLM publish credentials, which breaks the "human publishes" invariant.
