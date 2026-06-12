# AE-0008 — Wire ResearchTool URL Scraping into Editorial Workflow

Status: Review
Tier: T2
Priority: High
Type: Bugfix
Area: Backend
Owner: Unassigned
Agent Lane: architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-05
Updated: 2026-06-05

## Goal

Wire `PlaywrightResearchTool.scrape_url()` into the editorial carousel workflow so URL-type sources are scraped for text content before being passed to the LLM for content drafting.

## Problem

URL extraction code was removed in commit `18607ea` during the carousel pipeline consolidation. The `ResearchTool` protocol, `PlaywrightResearchTool` implementation, and DI singleton all still exist — but none are called from `start_from_subagent()` or `_sanitize_url_sources()` in `agents.py`. When a user provides URL sources, the LLM receives the URL string as content, cannot browse it, and fails with `"Invalid JSON response from LLM"`.

## Scope

- Create `sanitize_web_content()` in `input_sanitizer.py` — gentler sanitizer for scraped web content (strip HTML tags + injection patterns only; no lowercasing, no paren-stripping)
- Extract URL scraping into a standalone async helper function `_scrape_url_sources()` for testability
- Wire `ResearchTool` from the DI container into `build_rag_agent()` and use in `start_from_subagent()` closure
- In `start_from_subagent()`, pre-scrape sources tagged `SOURCE_TYPE_URL` before passing to `start_workflow()`
- Ensure `_sanitize_url_sources()` correctness (already tags `SOURCE_TYPE_URL`)
- Add/update tests for URL scraping in the workflow path
- Verify the content drafting phase receives scraped text (not URL strings)

## Non-Goals

- Adding a new DeepAgent phase or LangGraph node for URL extraction
- Adding search_web() fallback (DDG) to the carousel workflow (out of scope)
- Re-introducing `seed_urls` as a first-class workflow input field
- Frontend changes

## Modularization Alignment (2026-06-12)

Product bugfix (not debt) — schedule freely, but wire it the
target-architecture way so Phase 3 doesn't redo it:

- Inject `ResearchTool` through `build_rag_agent()` parameters
  (constructor injection); do NOT call `get_container()` from
  application/service code — AE-0078 baselines those violations and new
  ones are regressions.
- `_scrape_url_sources()` should be a pure async helper with the tool as
  an argument — it becomes a `ResearchProvider` port implementation in
  the plan's port list.
- `sanitize_web_content()` belongs with input sanitization (future
  knowledge/conversation boundary); keep it free of agent imports.

## Acceptance Criteria

- [ ] `sanitize_web_content()` created in `input_sanitizer.py` — strips HTML tags + injection patterns only (no lowercasing, no paren-stripping, no length truncation)
- [ ] `ResearchTool` is wired from the DI container into `build_rag_agent()` and used in `start_from_subagent()`
- [ ] URL scraping extracted into a standalone async helper `_scrape_url_sources()` for testability
- [ ] Sources with `source_type == "url"` are scraped via `research_tool.scrape_url()` before workflow starts
- [ ] Scraped content is sanitized with `sanitize_web_content()` (not `sanitize_llm_input()`)
- [ ] Scraped content replaces the raw URL in the source's `content` field
- [ ] Non-URL sources pass through unchanged
- [ ] If `scrape_url()` fails (network error, timeout), the source passes through with the original URL content (graceful degradation)
- [ ] Content drafting LLM receives scraped text instead of raw URLs
- [ ] Mixed URL/document sources: only URL items get scraped, document items pass through
- [ ] No type errors — `mypy --strict` passes
- [ ] Existing 772+ tests continue to pass

## Gherkin Scenarios

```gherkin
Feature: URL Source Extraction in Editorial Workflow

  Scenario: URL sources are scraped before LLM content drafting
    Given a workflow with a source of source_type "url"
    And the source content is "https://example.com/article"
    When start_from_subagent() processes the sources
    Then scrape_url() is called with "https://example.com/article"
    And the content field in EditorialWorkflowStartInput contains scraped text
    And the content drafting LLM receives scraped text, not the URL

  Scenario: Non-URL sources pass through unchanged
    Given a workflow with a source of source_type "document"
    And the source content is "Some pre-written text"
    When start_from_subagent() processes the sources
    Then scrape_url() is NOT called
    And the content field contains "Some pre-written text"

  Scenario: URL scraping fails gracefully
    Given a workflow with a URL source
    And scrape_url() raises a network error
    When start_from_subagent() processes the sources
    Then the workflow continues without error
    And the content field contains the original URL string

  Scenario: ResearchTool is None falls back gracefully
    Given build_rag_agent() is called without a research_tool
    When start_from_subagent() processes URL sources
    Then the workflow continues without error
    And the content field contains the original URL string

  Scenario: Mixed URL and document sources
    Given sources with both URL-type and document-type items
    When start_from_subagent() processes the sources
    Then URL items are scraped for content
    And document items pass through unchanged with original content

  Scenario: Scraped content is gently sanitized
    Given a URL source whose scraped content contains HTML, mixed case, and parentheses
    When sanitize_web_content() processes the content
    Then HTML tags are stripped
    And mixed case (e.g., "API", "JSON") is preserved
    And parentheses (e.g., function calls) are preserved
```

## Delta

### ADDED

- `sanitize_web_content()` function in `backend/src/rag_backend/agents/input_sanitizer.py`
- `_scrape_url_sources()` standalone helper in `backend/src/rag_backend/api/dependencies/agents.py`
- `ResearchTool` import in `agents.py`

### MODIFIED

- `backend/src/rag_backend/api/dependencies/agents.py`:
  - `build_rag_agent()` — wire `research_tool` from container and capture in closure
  - `start_from_subagent()` — call `_scrape_url_sources()` after sanitization loop
  - `start_editorial_workflow()` / `_start_editorial_workflow_for_rag()` — no change needed (source_urls handled separately)
- `backend/src/rag_backend/agents/input_sanitizer.py` — add `sanitize_web_content()`
- Tests in `tests/unit/agents/` — add tests for `_scrape_url_sources` and `sanitize_web_content`

### REMOVED

None.

## Affected Areas

- Backend: yes (agents.py, container.py)
- Frontend: no
- Database: no
- API: no (behavioral change only — sources with URLs now get scraped)
- Tests: yes (new unit tests for URL scraping in agents.py)
- Docs: no
- Prompts/LLM: no (input to LLM now has real content instead of URLs)
- Observability: recommended — add Langfuse trace on scrape_url call
- Deployment: no

## Dependencies

- Blocks: none
- Blocked by: none
- Related: AE-0004, AE-0005, AE-0007 (this is a runtime fix for the URL source workflow — all three prior tickets assumed sources were pre-extracted text)

## Implementation Plan

1. **Create `sanitize_web_content()`** in `backend/src/rag_backend/agents/input_sanitizer.py`:
   - New function that strips HTML tags via regex, strips injection patterns, preserves case and parens
   - Usage: `sanitize_web_content(scraped_text)` — called after scraping, before passing to workflow
   - Write unit tests in `test_input_sanitizer.py`

2. **Extract URL scraping helper** in `backend/src/rag_backend/api/dependencies/agents.py`:
   - Standalone async function `_scrape_url_sources(sources, research_tool)`:
   ```python
   async def _scrape_url_sources(
       sources: list[dict[str, str]],
       research_tool: ResearchTool | None,
   ) -> list[dict[str, str]]:
       """Scrape URL-type sources, replacing content with scraped text."""
       for item in sources:
           if item.get("source_type") == SOURCE_TYPE_URL and research_tool is not None:
               try:
                   scraped = await research_tool.scrape_url(item["content"])
                   item["content"] = sanitize_web_content(scraped)
               except Exception:
                   pass  # Graceful degradation — keep original URL string
       return sources
   ```
   - Testable in isolation with mocked `ResearchTool`

3. **Wire ResearchTool into `build_rag_agent()`**:
   - `build_rag_agent()` already receives `container` — use `research_tool = container.research_tool()`
   - Call `_scrape_url_sources(sanitized_sources, research_tool)` after sanitization loop in `start_from_subagent()` (line ~263)

4. **Import `ResearchTool` protocol** in `agents.py`:
   - `from rag_backend.domain.protocols import ResearchTool`

5. **Add tests** in `tests/unit/agents/test_carousel_pipeline_consolidation_unit.py`:
   - Test `_scrape_url_sources` with URL sources (scrape succeeds)
   - Test with non-URL sources (no scrape)
   - Test with scrape failure (graceful degradation)
   - Test with `research_tool=None` (passthrough)
   - Test `sanitize_web_content()` preserves case and parens

6. **Run typecheck + lint + tests**:
   - `cd backend && uv run mypy src/ && uv run ruff check src/ && uv run pytest`

7. **Verify content drafting LLM receives scraped text**:
   - Manual test: start workflow with a real URL source, check `phase_status` is not "failed"

## QA Checklist

- [x] Security reviewed
- [x] Code quality reviewed
- [x] Acceptance criteria validated
- [x] Edge cases tested
- [x] Orphan/unfinished code checked

## Progress Log

### 2026-06-05

Ticket created from architect research.

## Files Touched

- backend/.../api/dependencies/agents.py (structlog graceful-degradation logging)
  (sanitize_web_content + _scrape_url_sources + wiring + 21 tests pre-existed in base)

## Test Evidence

```
mypy strict: Success (389); ruff: clean
targeted: 21 passed; full suite: 1651 passed, 2 skipped
```

## QA Report

✅ PASS — Product batch QA (Cursor), WARN→fix→confirmation PASS. See `.agent/reports/AE-0008.qa.md` → `.agent/reports/product-ae0008-ae0009.qa.md`.Decision Log

Pending.

## Blockers

None.

## Final Summary

Pending.
