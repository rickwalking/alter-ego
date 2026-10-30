---
status: proposed
date: 2026-10-29
decision-makers: Pedro Marins
consulted: architecture review of the boost-bot design against the autopilot module
informed: delivery team
---

# ADR-0029: Owner-approved Instagram boosts

## Context and Problem Statement

A boost bot should rank organic Instagram posts and ask for a paid boost. The backend already reads insights for posts it published (`GET /api/instagram/insights`, ADR-0021 D11), but that route is editor/admin JWT only, covers only those posts, and omits likes, comments, media type and time. The bot holds only the autopilot `X-Api-Key`, which ADR-0020 limits to `/api/autopilot/*`.

There is no Marketing API client. The live token is an Instagram Login token (`graph.instagram.com`, scopes documented as `instagram_business_basic` and `instagram_business_content_publish`). That token cannot create ads. Boosting was an explicit non-goal of AE-0371.

## Decision Drivers

- The bot never holds a Meta token and never spends money.
- Spend happens only after the Telegram owner approves, and only while a kill switch is on.
- Reuse the autopilot key, Telegram owner gate, insights snapshot and Graph error handling.
- Leave the dashboard insights contract unchanged.
- A crash during ad creation must not leave a live, spending campaign.

## Considered Options

1. Give the bot the existing insights route and boost by hand in Ads Manager.
2. Let the bot call the Marketing API with a token of its own.
3. Add an API-key insights read, an owner-approved boost request, and a worker that creates paused ads on a separate System User token and activates them last.

## Decision Outcome

Chosen option 3, in three shippable phases. Phase 1 and phase 2 are useful with the kill switch off. Phase 3 does not run until this ADR is accepted and the Meta checklist in the architecture plan is done.

- `GET /api/autopilot/ig-insights` lists account media from the Instagram Login token, not only rows in `autopilot_runs` and the manual publish ledger. It adds type-specific metrics, rates and per-type medians. The JWT route and its seven-metric Graph call stay as they are.
- `POST /api/autopilot/boost-request` can only insert `pending_approval`. Approval, rejection and stop are Telegram owner callbacks (`is_owner`, `claim_update`, a strict `callback_data` regex). No API-key route transitions a request to `approved`.
- The worker calls `graph.facebook.com` with `META_ADS_ACCESS_TOKEN` only. Campaign, ad set, creative and ad are created `PAUSED`; each id is stored before the next step; `ACTIVE` is set only after `BOOST_ENABLED` is checked again. `BOOST_ENABLED` defaults to false.
- Caps are checked at create, at approval and at launch. The weekly window is a rolling 7 days by `created_at` in UTC. Version 1 accepts the engagement objective only.
- Unapproved requests expire after 12 hours. An approved request does not expire while the kill switch is off, so a phase-2 dry run does not throw away approvals. Caps are checked again at launch.
- Organic metrics and ad insights stay separate. The bot reads ad spend only from Postgres.

Option 1 cannot see posts made in the Instagram app, and it cannot record an approval. Option 2 gives an LLM a credential that can spend, which breaks the ADR-0020 rule that the bot does not hold publish credentials.

### Consequences

- Good: the bot can score posts after phase 1. Money cannot move until the owner approves and the kill switch is on.
- Good: a crash mid-launch resumes from stored ids and does not create a second campaign.
- Bad: a second Meta token, ad account and Page link have to be operated by hand.
- Bad: insights need `instagram_business_manage_insights`. A missing scope returns null metrics, not a hard error.
- Neutral: the dashboard snapshot table gains nullable columns. Writers update only the metrics they requested, so a dashboard refresh does not wipe bot-only columns.

## Validation

- API tests: 401/503 on the key, 422/409 on caps and duplicates, and no Marketing API call from an API-key route.
- Webhook tests: owner approve/reject, stranger ignored, duplicate update ignored.
- Worker tests: `BOOST_ENABLED=false` produces zero ads HTTP calls. A paused-then-activate sequence resumes after each step. Tokens do not appear in logs, responses or audit rows.

## Related

- [ADR-0020](0020-grokbot-autopilot.md) — scoped key and owner-gated Instagram side effects
- [ADR-0021](0021-content-mode-pov.md) D11 — dashboard insights
- Architecture plan: `.agent/reports/AE-0572.arch-plan.md`
