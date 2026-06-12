Feature: Workflow event emission is consistent with the database
  Workflow events reach Redis only after the corresponding audit record
  is committed to PostgreSQL (AE-0074). A rolled-back transaction must
  not leak events to the stream.

  Scenario: Event published only after commit
    Given a carousel workflow phase transition that emits an event
    When the surrounding transaction commits successfully
    Then the workflow audit record exists in PostgreSQL
    And the event is published to the content events stream afterwards

  Scenario: Rolled-back transaction publishes nothing
    Given a carousel workflow phase transition that emits an event
    When the surrounding transaction rolls back before commit
    Then no workflow audit record exists in PostgreSQL
    And no event is published to the content events stream

  Scenario: Publish failure after commit does not break the request
    Given a committed workflow phase transition with a pending event
    When the Redis publish fails
    Then the request completes successfully
    And the failure is logged with the event identifier
