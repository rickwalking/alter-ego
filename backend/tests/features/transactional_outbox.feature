Feature: Transactional outbox (AE-0130)
  As the workflow event system
  I want events written to a durable outbox in the state transaction and relayed at-least-once
  So that release/workflow events are not lost if Redis is unavailable post-commit

  Background:
    Given a workflow event service backed by an in-memory publisher

  Scenario: event persisted in the state transaction
    When a release event is emitted
    Then an outbox row is committed atomically with the state change

  Scenario: rollback discards the outbox row
    When a release event is emitted
    And the transaction is rolled back
    Then no outbox row exists and nothing is published

  Scenario: the relay publishes unpublished rows
    Given a release event has been emitted
    When the relay runs
    Then the event is published to the content stream and the row is marked published

  Scenario: the relay is idempotent
    Given a release event has been emitted and relayed
    When the relay runs again
    Then the event is not republished (single delivery)

  Scenario: the relay is at-least-once
    Given a release event has been emitted
    And the first relay pass fails to publish
    When the relay runs again
    Then the still-unpublished event is delivered with the same result

  Scenario: the relayed payload is byte-identical to the legacy stream event
    Given a release event has been emitted
    When the relay runs
    Then the published payload has the exact field set and values emit produced
