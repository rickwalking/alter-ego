Feature: A researcher subagent can browse a URL during carousel creation (AE-0249)

  The researcher subagent wraps the existing PlaywrightResearchTool
  (scrape_url / search_web) as LangChain @tool adapters and runs in an
  isolated context. The adapters are thin façades that delegate to the
  application service through the ResearchTool Protocol — no business logic
  and no infrastructure lives in the agent package (ADR-0016). Deterministic
  carousel phases (outline, content, export, DB sync, persona gate) stay raw
  LangGraph nodes and are NEVER converted into task-delegated subagents
  (ADR-007). The subagent specs use the DeepAgents tools/prompt/model fields.

  Background:
    Given the carousel research tooling

  Scenario: The agent browses a pasted URL and synthesizes sources
    Given a user provides a URL during carousel research
    When the researcher subagent runs with the scrape_url tool
    Then it fetches the page content and returns synthesized sources

  Scenario: The scrape_url adapter delegates to the service via the Protocol
    Given a ResearchTool Protocol implementation
    When the scrape_url @tool adapter is invoked with a URL
    Then it delegates to the service scrape_url and returns the page content

  Scenario: The search_web adapter delegates to the service via the Protocol
    Given a ResearchTool Protocol implementation
    When the search_web @tool adapter is invoked with a query
    Then it delegates to the service search_web and returns formatted sources

  Scenario: A scrape failure degrades gracefully
    Given the scrape_url tool fails on an unreachable URL
    When the researcher subagent runs
    Then the failure is reported and research continues without the URL

  Scenario: The scrape_url adapter blocks SSRF targets (QA F-1)
    Given an LLM-supplied URL targeting an internal or non-http(s) resource
    When the scrape_url @tool adapter is invoked
    Then it returns a blocked message and never calls the scraping service

  Scenario: Deterministic phases stay LangGraph nodes
    Given the carousel workflow runs
    When the outline and export phases execute
    Then they run as deterministic LangGraph nodes, not task-delegated subagents

  Scenario: Subagent specs use the DeepAgents tools/prompt/model fields
    Given the researcher subagent spec
    Then it exposes tools, a prompt, and a description (DeepAgents fields)
    And it grants the scrape_url, search_web, and search_documents tools
