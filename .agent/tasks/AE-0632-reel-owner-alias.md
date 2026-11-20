# AE-0632 — Repost drafts refuse the account's own Reels (Graph owner id alias)

Status: In Development
Tier: T1
Priority: Critical
Type: Bug
Area: Backend
Owner: Pedro
Agent Lane: developer → qa → release
Branch: fix/ae-0631-reel-cover-columns-oneshot
Kanban Card: TBD
Created: 2026-11-20
Updated: 2026-11-20

## Goal

`POST /api/autopilot/repost` accepts a Reel the account owns, as listed by `GET /api/autopilot/reels`.

## Problem

On 2026-11-20 the scout listed 20 Reels, then got 404 `reel_not_found` for one of them (media 18077368361200866).
A Graph probe from the prod backend showed:

- `META_IG_USER_ID` is `17841480011497925`, and `GET /17841480011497925?fields=id` answers `"id": "39207367818909157"`.
- The Reel's `owner` is `{"id": "39207367818909157"}`: the same account under its other id.

The ownership check compared `owner.id` to the configured id only, so it refused every Reel. AE-0626's QA change
(fail closed on a missing owner) was right; the strict compare against one id was the bug.

## Scope

- `GraphReelGateway._owned`: accept `owner.id` equal to the configured id, or to the id Graph reports for the
  configured account. Look that id up with `GET /{ig_user_id}?fields=id` only on a mismatch, once per gateway.
  A missing or empty owner, or any other id, is still not found.
- Contract doc: the owner rule, and what the probe showed (collaborators edge unsupported, `follows` null for Reels,
  the 15-per-request duration probe budget).

## Non-Goals

- No collaborators fallback: the edge does not exist for this account's API, so the scout sends collaborators
  explicitly.

## Acceptance Criteria

- [x] AC1 A Reel whose owner is the id Graph reports for the configured account is found; the account id is
  fetched once and only after a mismatch.
- [x] AC2 A Reel whose owner is the configured id is found without the extra call.
- [x] AC3 Another account's id, an empty owner id or no owner is not found (404).
- [ ] AC4 After deploy, the scout's draft for media 18077368361200866 answers 202.

## Gherkin

`backend/tests/features/reel_owner_alias_ae0632.feature`

## Files Touched

- `backend/src/rag_backend/modules/autopilot/infrastructure/reels_gateway.py`
- `backend/tests/unit/modules/autopilot/test_repost_graph_ae0629.py`
- `backend/tests/features/reel_owner_alias_ae0632.feature`
- `docs/architecture/grokbot-reels-repost.md`

## Test Evidence

- `uv run pytest tests/unit/modules/autopilot` → 1360 passed.
- Single gates format, lint, lint-diff, strict-diff, type, imports, arch-ratchet, docstrings, dead-code,
  gherkin-refs, comments, integrity, duplication → PASS.

## Decision Log

- 2026-11-20: Kept the fail-closed rule and added the alias rather than dropping the check, so a foreign media id
  still answers 404.
