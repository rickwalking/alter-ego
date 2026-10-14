# AE-0352 — Signal collectors (X via ddgs web search, HN, HF, RSS, Bluesky, GitHub) + GET /api/autopilot/signals

Status: Dev Complete
Tier: T2
Priority: High
Type: Feature
Area: backend
Owner: Grok (Cursor CLI, grok-4.7-high)
Agent Lane: developer → qa → release
Branch: feat/ae-0352-autopilot-signal-collectors
Kanban Card: TBD
Created: 2026-10-13
Updated: 2026-10-13
Parent: AE-0348

## Goal

Collect free, typed, deduped AI-trend signals in the backend and serve them as one JSON bundle to the scout.

## Problem

No trend ingestion exists. Official X paths are paid; xcancel returned HTTP 451 (suspended, legal proceedings) and nitter.net serves a bot challenge — but `ddgs` `site:x.com` queries return post URLs + text snippets (verified 2026-10-13).

## Scope

- `Collector` protocol in `domain/ports.py`: `async collect(window: CollectWindow) -> list[Signal]`; `Signal` Pydantic model {source, url, title, text, posted_at, handle?, score_hint?}.
- `XWebSearchCollector` (doc §5.1): reuse the existing `ddgs` client pattern from `application/services/tools/research_tool.py:26` (asyncio.to_thread); query templates in `constants.py`; `timelimit="d"`, `max_results=10`, ≤6 queries/run, 2–5 s jittered spacing; keep only URLs matching `^https://(x|twitter)\.com/[A-Za-z0-9_]{1,15}/status/\d+$`, canonicalise to x.com; `posted_at` from snowflake `(id >> 22) + 1288834974657` ms; drop >48 h; never request x.com itself.
- `XPostResolver` port with `NoneResolver` (default) and `MirrorResolver` (rewrites to `https://{AUTOPILOT_X_MIRROR_HOST}/{handle}/status/{id}`; non-2xx or `_is_block_page`-style body → return None). Selected by `AUTOPILOT_X_RESOLVER=none|mirror`.
- `HackerNewsCollector`: `hn.algolia.com/api/v1/search?tags=story&query=<kw>&numericFilters=points>100,created_at_i><ts>`.
- `HuggingFacePapersCollector`: `huggingface.co/api/daily_papers`.
- `RssCollector`: feed list in constants (OpenAI, Anthropic, Google AI, Meta AI blogs, The Verge AI); use `feedparser` only if already a dependency, else stdlib `xml.etree` with defusedxml.
- `BlueskyTrendsCollector`: `app.bsky.unspecced.getTrends` (no auth).
- `GitHubSearchCollector`: Search API `created:>D sort:stars topic:llm` with optional token.
- `SignalsService.collect_all()`: run collectors concurrently with per-collector timeout (20 s) and isolation (one failing collector → logged + skipped, bundle still returned with `errors[]`); dedupe by canonical URL; cap 200 signals; cache result 30 min.
- `GET /api/autopilot/signals` (API-key auth from AE-0351) returns `{generated_at, signals[], errors[]}`.

## Non-Goals

- Reddit, Google Trends, Product Hunt, paid X/xAI.
- Ranking (Grok does it in AE-0360).
- Enabling the mirror resolver.

## Acceptance Criteria

- [x] WHEN all collectors succeed THE endpoint SHALL return deduped signals with `source` in {x_search, hn, hf_papers, rss, bluesky, github}.
- [x] WHEN one collector raises or times out THE endpoint SHALL still return 200 with the others' signals and an `errors[]` entry naming the failed source.
- [x] WHEN `ddgs` returns a non-status x.com URL (profile, search page) THE X collector SHALL drop it.
- [x] WHEN an X status id decodes to older than 48 h THE X collector SHALL drop it.
- [x] WHEN `AUTOPILOT_X_RESOLVER=mirror` and the mirror returns 451 THE resolver SHALL return None and the snippet text SHALL be kept.
- [x] WHEN tests run THE network SHALL be fully mocked (respx / fakes); no live HTTP in CI.

## Gherkin Scenarios

```gherkin
Feature: Autopilot signal collection

  Scenario: Bundle combines all free sources
    Given every collector returns at least one signal
    When the scout requests the signals bundle
    Then the bundle contains signals from x_search, hn, hf_papers, rss, bluesky and github
    And no URL appears twice

  Scenario: One source failing does not fail the bundle
    Given the Bluesky collector times out
    When the scout requests the signals bundle
    Then the response status is 200
    And errors contains "bluesky"

  Scenario: X search keeps only recent status posts
    Given ddgs returns a profile URL, a 3-day-old status and a 2-hour-old status
    When the X collector runs
    Then only the 2-hour-old status is kept with its snippet text

  Scenario: Mirror resolver falls back on legal block
    Given the resolver is "mirror" and the mirror answers HTTP 451
    When a status URL is resolved
    Then the resolver returns nothing and the snippet is used
```

## Delta

### ADDED

- `backend/src/rag_backend/modules/autopilot/infrastructure/collectors/*.py`
- `backend/src/rag_backend/modules/autopilot/application/signals_service.py`
- `GET /api/autopilot/signals`
- `backend/tests/features/autopilot_signals.feature`

### MODIFIED

- `infrastructure/config/settings.py` (AUTOPILOT_X_RESOLVER, AUTOPILOT_X_MIRROR_HOST, GITHUB_TOKEN optional)

### REMOVED

- None.

## Affected Areas

- Backend: collectors
- API: signals route
- Tests: mocked HTTP

## Dependencies

- Blocks: AE-0353, AE-0360
- Blocked by: AE-0350, AE-0351
- Related: doc §5, §5.1

## Implementation Plan

1. Feature file first.
2. Signal model + Collector protocol + snowflake helper (pure function, property-test it).
3. One collector per file, each with fixture-based tests.
4. SignalsService with timeout/isolation/dedupe/cache.
5. Route.

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
- [ ] No live network in tests
- [ ] No request to x.com or any mirror when resolver=none

## Progress Log

### 2026-10-13 00:00

Ticket created from docs/architecture/grokbot-autopilot.md (ticket #3).

### 2026-10-13 19:50

Status moved to In Development on `feat/ae-0352-autopilot-signal-collectors`.
Feature file written before implementation.

### 2026-10-13 20:55

`bash scripts/ci/gate-capture.sh backend` exit 0 (20 pass, 0 fail, 0 skip). Pytest 3070 passed / 2 skipped. Dev summary: `.agent/reports/AE-0352.dev-summary.md`.

### 2026-10-13 21:00

Moved to Dev Complete.

### 2026-10-13 21:12

Verifier capture exited 3 on `backend:strict-diff`, `backend:integrity`, and `backend:mutation`. Each died in `mktemp` or pytest `TemporaryFile` because `/tmp` had no free inodes. No gate threshold or test was changed. After the stale pytest temp dirs were removed, `bash scripts/ci/gate-capture.sh backend` exited 0 (20 pass, 0 fail, 0 skip). Pytest 3070 passed / 2 skipped. Mutation score 79.39%. Status stays Dev Complete.

## Files Touched

- `backend/tests/features/autopilot_signals.feature`
- `backend/tests/unit/autopilot/`
- `backend/tests/integration/test_autopilot_signals.py`
- `backend/tests/integration/test_autopilot_api_key.py`
- `backend/src/rag_backend/modules/autopilot/domain/signals.py`
- `backend/src/rag_backend/modules/autopilot/domain/snowflake.py`
- `backend/src/rag_backend/modules/autopilot/domain/x_status.py`
- `backend/src/rag_backend/modules/autopilot/domain/ports.py`
- `backend/src/rag_backend/modules/autopilot/application/signals_service.py`
- `backend/src/rag_backend/modules/autopilot/application/signal_cache.py`
- `backend/src/rag_backend/modules/autopilot/infrastructure/collectors/`
- `backend/src/rag_backend/modules/autopilot/api/router.py`
- `backend/src/rag_backend/modules/autopilot/bootstrap.py`
- `backend/src/rag_backend/modules/autopilot/constants.py`
- `backend/src/rag_backend/infrastructure/config/settings.py`
- `backend/.env.example`
- `backend/pyproject.toml`
- `backend/uv.lock`

## Test Evidence

- `backend/tests/features/autopilot_signals.feature` — all six sources, one source timing out, recent X posts only, mirror 451, cache reuse, 200-signal cap.
- `backend/tests/unit/autopilot/` — snowflake round-trip, X URL filter and 48h cutoff, mirror resolver, HN/HF/Bluesky/GitHub parsers, RSS/Atom/sitemap, service isolation, cache, wiring. Network is respx or a fake search client.
- `backend/tests/integration/test_autopilot_signals.py` — `GET /api/autopilot/signals` returns 200 with every source and no duplicate URL; a Bluesky timeout stays 200 and names `bluesky` in `errors`.
- Gate proof: `.agent/reports/AE-0352.dev-summary.md`.

## QA Report

Pending.

## Decision Log

See ADR-0020.

### 2026-10-13

- Anthropic has no RSS feed (the documented URLs returned 404 on 2026-10-13). The collector reads `https://www.anthropic.com/sitemap.xml` and keeps paths containing `/news/`.
- The Meta AI blog RSS also returned 404. The collector uses `https://engineering.fb.com/category/ml-applications/feed/`.
- Google AI uses `https://blog.google/innovation-and-ai/technology/ai/rss/`.
- GitHub search uses `topic:llm created:>` with a 7-day lookback (`GITHUB_LOOKBACK_DAYS`). The architecture table left the date window unspecified.
- The mirror resolver returns visible text. It does not parse like or repost counts. The default resolver stays `none`.
- Shipped X queries are the three examples in the architecture doc. The cap remains six. Six queries at the 5s spacing ceiling can exceed the 20s collector timeout, so the default list stays at three.

## Blockers

None.

## Final Summary

Pending.
