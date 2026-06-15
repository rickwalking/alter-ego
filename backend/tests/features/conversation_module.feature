Feature: Conversation module skeleton, facade, shims, and ChatAgentFactory (AE-0100)
  As a backend maintainer extracting the conversation bounded context
  I want a behavior-preserving module facade with object-identity repo shims
  and a ChatAgentFactory port wrapping the existing builders
  So that routes/streaming can later delegate without any agent behavior change

  Scenario: Repository ports re-export to identical objects (object-identity shim)
    Given the canonical ConversationRepository/MessageRepository Protocols at the legacy path
    When the module re-exports them from modules.conversation.domain.ports
    Then the re-exported objects are the SAME objects (A is B) so ~50+ callers stay valid

  Scenario: Conversation/Message entities re-export to identical objects
    Given the canonical Conversation/Message entities at the legacy domain.models path
    When the module re-exports them from modules.conversation.domain.models
    Then the re-exported entities are the SAME class objects

  Scenario: The facade exposes the documented public API
    Given the conversation module facade
    When a consumer imports from rag_backend.modules.conversation
    Then ConversationService, ChatAgentFactory, LegacyChatAgentFactory, and bootstrap_module are available

  Scenario: bootstrap wires the module via manual DI (no global container)
    Given pre-built request-scoped adapters in a ConversationAdapters bundle
    When bootstrap_module(platform, adapters) is called
    Then it returns a ConversationModule exposing the ConversationService and the bound agent factory

  Scenario: The factory builds the RAGAgent when project_id metadata is present
    Given a conversation whose metadata carries a project_id and a user_id
    When LegacyChatAgentFactory.build_for_conversation is called
    Then it delegates to build_agent_for_conversation and yields the RAG agent (carousel-capable)

  Scenario: The factory builds the AlterEgoAgent when no project_id metadata is present
    Given a conversation with empty metadata
    When LegacyChatAgentFactory.build_for_conversation is called
    Then it delegates to build_agent_for_conversation and yields the AlterEgo agent (KB only)

  Scenario: The factory binds the request-scoped session and container
    Given a LegacyChatAgentFactory constructed with a db session and a container
    When build_for_conversation is called for a conversation
    Then the bound db and container are forwarded to build_agent_for_conversation unchanged
