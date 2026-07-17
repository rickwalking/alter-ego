Feature: Web research enrichment in the initial editorial workflow
  AE-0317: workflow start navigates user-provided URL sources (Playwright) and
  researches the topic on DuckDuckGo, deterministically and uniformly across all
  entry points, with SSRF guarding, bounded latency, and graceful degradation.

  Scenario: URL source is navigated and its content informs research
    Given a carousel project with a source of type "url" pointing to a reachable page
    When the editorial workflow is started
    Then the research findings are derived from the scraped page text
    And the source content is sanitized web content, not the bare URL

  Scenario: Note source embedding a bare URL is also navigated
    Given a source whose content is exactly an http(s) URL without a url source_type
    When the editorial workflow is started
    Then that source is navigated like a url source

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

  Scenario: Scrape volume is capped
    Given more url sources than the scrape cap
    When the editorial workflow is started
    Then only the first 5 url sources are navigated
    And the remaining url sources pass through unchanged

  Scenario: Enrichment disabled restores legacy behavior
    Given research enrichment is disabled
    When the editorial workflow is started with url sources
    Then no scraping and no web search occur
    And sources reach synthesis unchanged

  Scenario: Search failure is non-fatal
    Given the web search raises an exception
    When the editorial workflow is started
    Then the workflow start succeeds with only the provided sources

  Scenario: Researcher subagent is registered in the chat pipeline
    Given a RAG agent built with carousel tool access and a research tool
    When its subagents are composed
    Then the researcher subagent is included alongside the editorial subagent
