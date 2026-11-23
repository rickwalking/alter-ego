# AE-0640 — The scout can override the weekly repost cap

Status: In Development
Tier: T1
Priority: High
Type: Feature
Area: Backend
Owner: Pedro
Agent Lane: developer → qa → release
Branch: fix/ae-0640-repost-cap-override
Kanban Card: TBD
Created: 2026-11-23
Updated: 2026-11-23

## Goal

When Pedro asks GrokBot for an extra Reel repost in a week that already has two drafts, the scout can submit it.

## Problem

2026-11-23: GrokBot's `POST /api/autopilot/repost` answered 422 `weekly_cap_reached`. The week held a published
repost (2026-11-20 22:30 UTC) and a rejected draft (2026-11-20 21:58 UTC). The cap (`WEEKLY_CAP = 2`) is a code
constant, so neither the scout nor Pedro could send the extra repost before Friday.

## Scope

- `RepostCreate` and `RepostDraft` gain `override_weekly_cap: bool = False`.
- `check_eligibility` skips only the weekly cap when the flag is set; every other refusal still applies.
- The flag enters `request_hash` only when `true`, so stored drafts keep their hash and still replay.
- The `created` log line records `cap_override`.
- `docs/architecture/grokbot-reels-repost.md` documents the flag.

## Non-Goals

- The default cap value and the counted statuses do not change.
- Owner approval on Telegram is still required for every draft.

## Acceptance Criteria

- [ ] Without the flag, a third draft in 7 days is still refused with 422 `weekly_cap_reached`.
- [ ] With `override_weekly_cap: true`, the draft is stored `pending_approval` and the log records `cap_override`.
- [ ] With the flag, the other rules (for example `too_recent`) still refuse.
- [ ] A body without the flag hashes exactly as before.

## Affected Areas

- [x] Backend
- [ ] Frontend
- [x] Tests
- [x] Docs

## Dependencies

None.

## Progress Log

### 2026-11-23

Ticket created from GrokBot's refused extra repost.

## Files Touched

- `backend/src/rag_backend/modules/autopilot/api/repost_schemas.py`
- `backend/src/rag_backend/modules/autopilot/api/repost_mapping.py`
- `backend/src/rag_backend/modules/autopilot/domain/repost.py`
- `backend/src/rag_backend/modules/autopilot/domain/repost_rules.py`
- `backend/src/rag_backend/modules/autopilot/application/repost_drafts.py`
- `backend/tests/features/autopilot_repost_cap_override_ae0640.feature` (new)
- `backend/tests/unit/modules/autopilot/test_repost_cap_override_ae0640.py` (new)
- `docs/architecture/grokbot-reels-repost.md`

## Test Evidence

Pending.

## QA Report

Pending.

## Blockers

None.
