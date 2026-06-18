Feature: Composition-root startup hardening
  As an operator deploying the RAG backend
  I want startup guards to reject ephemeral configuration in production
  So that workflow state is durable and default-preset carousels do not fail late

  # AE-0213 — durable LangGraph checkpointer in prod
  Scenario: Production rejects a non-durable (memory) checkpointer
    Given the environment is production
    And CAROUSEL_CHECKPOINT_BACKEND is memory
    When startup validations run
    Then startup fails with a durable-checkpointer error

  Scenario: Production rejects a disabled checkpointer
    Given the environment is production
    And CAROUSEL_CHECKPOINT_BACKEND is disabled
    When startup validations run
    Then startup fails with a durable-checkpointer error

  Scenario: Production accepts a postgres checkpointer
    Given the environment is production
    And CAROUSEL_CHECKPOINT_BACKEND is postgres
    When startup validations run
    Then the checkpointer guard passes

  Scenario: Development tolerates a non-durable checkpointer with a warning
    Given the environment is development
    And CAROUSEL_CHECKPOINT_BACKEND is memory
    When startup validations run
    Then the checkpointer guard warns instead of failing
