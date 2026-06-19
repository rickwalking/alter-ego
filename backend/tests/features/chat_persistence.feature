Feature: Chat agents have a single canonical persistence path (ADR-0013 / AE-0247)

  The two chat Deep Agents (rag_agent, alter_ego_agent) persist conversation
  state to message_repository only. They are NEVER given a LangGraph
  checkpointer — a second durable write path would be the AE-0163 dual-write
  data-loss class. A build-time guard enforces this invariant.

  Background:
    Given message_repository is the canonical chat-persistence store

  Scenario: A chat turn writes only to the message repository
    Given a chat Deep Agent processes a user message
    When the turn completes
    Then the message is persisted to message_repository
    And no LangGraph checkpoint write occurs for that thread

  Scenario: Wiring a chat checkpointer is rejected (guard trips)
    Given the chat-agent build path is asked to attach a checkpointer
    When assert_no_chat_checkpointer runs with a non-None checkpointer
    Then it raises ChatCheckpointerError naming the AE-0163 dual-write risk
    And chat-agent construction fails loudly

  Scenario: The Option-A default builds without a checkpointer
    Given a chat Deep Agent is constructed
    When the build path runs assert_no_chat_checkpointer(None)
    Then no error is raised
    And the agent is created with no checkpointer
