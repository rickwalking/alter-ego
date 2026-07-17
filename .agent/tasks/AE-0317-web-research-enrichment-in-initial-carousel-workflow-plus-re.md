# AE-0317 — web research enrichment in initial carousel workflow plus researcher subagent registration

Status: Ready
Tier: T2
Priority: High
Type: Feature
Area: backend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0317-0318-research-enrichment
Kanban Card: TBD
Created: 2026-07-17
Updated: 2026-07-17

## Goal

The initial editorial carousel workflow (`POST /carousels/{id}/workflow/start`)
performs real web research: user-provided URL sources are navigated (Playwright
scrape) and the topic is researched on DuckDuckGo, deterministically and uniformly
across ALL entry points (HTTP route, RAG chat tool, DeepAgents subagent) — and the
orphaned `researcher` subagent (AE-0249) is registered in its designed home, the
RAG chat pipeline.

## Problem

The direct HTTP route passes sources sanitized-as-is to a plain LLM summarization
(`synthesize_research`) with no tools — a `source_type: "url"` source reaches the
LLM as a bare URL string, and the model answers "I am unable to access external
links", which becomes a useless "research finding" (observed in prod 2026-07-17,
project f9e3e199, Langfuse trace 375358d6…). Scraping exists only as a route-edge
pre-step on the two RAG-chat paths (`_scrape_url_sources`,
`api/dependencies/agents.py:200-231,240-241,358`) and that edge applies **no SSRF
guard** — `is_safe_research_url` is only enforced in the LangChain @tool adapter
(`agents/tools/research_tools.py:66`). Meanwhile `build_researcher_subagent`
(AE-0249, ADR-0015) is dead code: `RAGAgent._build_subagents()` returns only the
editorial subagent (`agents/rag_agent.py:120-124`); repo-wide, only its own tests
reference it.

Full analysis: `.agent/reports/AE-0317.arch-plan.md` (facts F1–F10).

## Scope

- New `application/services/carousel/research_enrichment.py`: deterministic
  `enrich_sources(sources, topic, config)` run by
  `EditorialWorkflowService.start_workflow` BEFORE `synthesize_research`:
  - Scrape sources where `source_type == "url"` or content is a bare http(s) URL
    (same superset rule as today's RAG edge), guarded by `is_safe_research_url`,
    per-URL graceful degradation (keep original content, warn log), capped
    (max 5 URLs) and bounded (Semaphore(2) concurrency).
  - DuckDuckGo topic search via `ResearchTool.search_web`; append top 3 hits as
    synthetic sources (`source_type: "web_search"`, snippet as content). Snippets
    only — search hits are NOT scraped. Non-fatal on failure.
  - Constants in `domain/constants/research_enrichment.py`; scraped text passes
    `sanitize_web_content`.
- `EditorialWorkflowConfig` gains `research_tool: ResearchTool | None = None`;
  wire `container.research_tool()` at `build_editorial_workflow_service` and
  `build_rag_agent`. `None` → enrichment no-ops (CI-safe).
- Delete `_scrape_url_sources` and its two call sites in
  `api/dependencies/agents.py` (single choke point now in the service; closes the
  unguarded SSRF edge).
- Register the researcher subagent: `RAGAgent._build_subagents()` also returns
  `build_researcher_subagent(...)` when carousel tool access is present.
- Settings kill-switch: `research_enrichment_enabled: bool = True`; disabled →
  byte-identical legacy behavior.
- Gherkin `.feature` + unit/integration tests (mock `ResearchTool` Protocol; CI
  has no network).

## Non-Goals

- No agentic/DeepAgents loop inside the workflow research phase (ADR-0007:
  deterministic phases stay deterministic).
- No scraping of DDG search hits (snippets only; future ticket if wanted).
- No new endpoints, no DB/schema changes, no frontend changes.
- No change to synthesis JSON parsing/caching (that is AE-0318).

## Acceptance Criteria

- [ ] `POST /carousels/{id}/workflow/start` with a `url` source produces research
      findings derived from the scraped page text (mocked in tests), not from the
      bare URL string.
- [ ] Topic search appends at most 3 `web_search` sources; search failure does not
      fail the workflow start.
- [ ] Unsafe URLs (private/loopback/link-local IPs, non-http(s) schemes) are never
      scraped from ANY entry point; original content passes through and
      `research_url_blocked` is logged.
- [ ] Scrape timeout/error on any URL degrades gracefully (original content kept,
      `research_url_scrape_failed` logged, workflow proceeds).
- [ ] At most 5 URL sources are scraped, at most 2 concurrently.
- [ ] All three entry points (HTTP route, `_start_editorial_workflow_for_rag`,
      `start_from_subagent`) get enrichment via the single service path;
      `_scrape_url_sources` no longer exists in `api/dependencies/agents.py`.
- [ ] `research_enrichment_enabled=false` restores prior behavior exactly.
- [ ] `RAGAgent._build_subagents()` includes the researcher subagent when carousel
      tool access is present; orphan-detection no longer flags
      `build_researcher_subagent`.
- [ ] `research_tool=None` (CI/tests) → no-op, no network attempted, DI resolution
      needs no external keys.
- [ ] `tests/features/research_enrichment.feature` covers happy/edge/failure;
      tests reference scenarios in comments.

## Gherkin Scenarios

```gherkin
Feature: Web research enrichment in the initial editorial workflow

  Scenario: URL source is navigated and its content informs research
    Given a carousel project with a source of type "url" pointing to a reachable page
    When the editorial workflow is started
    Then the research findings are derived from the scraped page text
    And the source content is sanitized web content, not the bare URL

  Scenario: Topic is researched on DuckDuckGo
    Given a carousel project with a topic and note sources
    When the editorial workflow is started
    Then at most 3 additional sources of type "web_search" are appended
    And each carries the search hit title, url, and snippet as content

  Scenario: Unsafe URL is blocked, workflow proceeds
    Given a source whose content is "http://169.254.169.254/latest/meta-data"
    When the editorial workflow is started
    Then the URL is not scraped
    And the original source content is preserved
    And a research_url_blocked warning is logged

  Scenario: Dead link degrades gracefully
    Given a source of type "url" whose page times out
    When the editorial workflow is started
    Then the workflow start succeeds
    And the source keeps its original URL content
    And a research_url_scrape_failed warning is logged

  Scenario: Enrichment disabled restores legacy behavior
    Given research_enrichment_enabled is false
    When the editorial workflow is started with url sources
    Then no scraping and no web search occur
    And sources reach synthesis unchanged

  Scenario: Search failure is non-fatal
    Given the web search raises an exception
    When the editorial workflow is started
    Then the workflow start succeeds with only the provided sources

  Scenario: Researcher subagent is registered in the chat pipeline
    Given a RAG agent built with carousel tool access
    When its subagents are composed
    Then the researcher subagent is included alongside the editorial subagent
```

## Delta

### ADDED

- `application/services/carousel/research_enrichment.py`
- `domain/constants/research_enrichment.py`
- `Settings.research_enrichment_enabled`
- `tests/features/research_enrichment.feature` + unit/integration tests

### MODIFIED

- `application/services/carousel/editorial_workflow_service.py` (config field +
  enrichment call in `start_workflow`)
- `api/dependencies/agents.py` (remove edge scraping; wire research_tool into
  workflow config)
- `api/routes/carousels/editorial_workflow_support.py` /
  `build_editorial_workflow_service` seam (wire research_tool)
- `agents/rag_agent.py` (`_build_subagents` registers researcher)

### REMOVED

- `_scrape_url_sources` + `_URL_PATTERN` route-edge duplication in
  `api/dependencies/agents.py`

## Affected Areas

- Backend: application service, DI wiring, agents
- Frontend: none
- Database: none
- API: no shape change (behavioral only)
- Tests: feature file, unit, integration
- Docs: arch plan `.agent/reports/AE-0317.arch-plan.md`
- Prompts/LLM: none
- Observability: new structlog events (research_url_blocked,
  research_url_scrape_failed, research_search_failed, research_url_cap_hit)
- Deployment: env kill-switch `RESEARCH_ENRICHMENT_ENABLED` (default true)

## Dependencies

- Blocks: —
- Blocked by: —
- Related: AE-0318 (ships first; independent), AE-0249 (completes its unfinished
  registration — add Decision Log note there), ADR-0007, ADR-0015, ADR-0016

## Implementation Plan

1. Constants + `research_enrichment.py` with unit tests (stub ResearchTool).
2. Thread `research_tool` through `EditorialWorkflowConfig` + both build sites.
3. Call `enrich_sources` in `start_workflow`; settings toggle.
4. Delete edge scraping in `agents.py`; adjust its tests.
5. Register researcher subagent in `rag_agent.py`.
6. Feature file + integration consolidation test (all entry points share path).
7. Full gates + integrity + QA.

## QA Checklist

- [ ] Security reviewed (SSRF guard at single choke point; sanitize_web_content)
- [ ] Code quality reviewed (≤3 args via config objects; constants file; ≤400-line files)
- [ ] Acceptance criteria validated
- [ ] Edge cases tested (cap, concurrency, timeout, disabled, None tool)
- [ ] Orphan/unfinished code checked (researcher no longer orphaned)

## Progress Log

### 2026-07-17

Ticket created from `.agent/reports/AE-0317.arch-plan.md`; architect validation
complete (no new ADR required — implements ADR-0015/0016, preserves ADR-0007).

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Decision Log

- Research phase stays deterministic (ADR-0007); researcher subagent registered in
  chat pipeline per AE-0249's original design; both share one `ResearchTool`.
- Search hits contribute snippets only (no scrape) — bounded latency; revisit later.
- SSRF guard consolidated at the single service choke point (fixes pre-existing
  unguarded RAG edge).

## Blockers

None.

## Final Summary

Pending.
