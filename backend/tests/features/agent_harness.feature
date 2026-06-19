Feature: A shared harness composes Deep Agents with the correct persistence defaults (AE-0248)

  The shared harness (agents/harness/) is the single composition surface for the
  carousel orchestrator and the chat Deep Agents. build_deep_agent enforces the
  persistence defaults in one place: chat agents get summarization but NO
  checkpointer (ADR-0013 / AE-0247); workflow agents may keep their single-writer
  checkpointer. The harness stays generic — it never imports rag_backend.application.

  Background:
    Given the shared Deep Agents harness build surface

  Scenario: A chat agent is built via the harness builder with summarization
    Given a DeepAgentConfig for a chat agent with a SummarizationMiddleware preset
    When build_deep_agent runs
    Then a Deep Agent is composed via create_deep_agent
    And the summarization middleware is wired so context-window growth is capped
    And no LangGraph checkpointer is attached to the chat agent

  Scenario: The summarization preset caps chat context-window growth
    Given the harness summarization preset
    Then it triggers a summary once the message count exceeds the threshold
    And it keeps only the most recent messages verbatim

  Scenario: Wiring a chat checkpointer through the harness is rejected
    Given a DeepAgentConfig requests a checkpointer for a chat agent
    When build_deep_agent runs
    Then the AE-0247 guard raises ChatCheckpointerError and the build fails

  Scenario: A workflow agent may keep its single-writer checkpointer
    Given a DeepAgentConfig for a workflow agent carrying a checkpointer
    When build_deep_agent runs
    Then the guard does not trip
    And the checkpointer is passed through to create_deep_agent
