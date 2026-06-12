Feature: SSE event names are frozen during the migration
  As a platform maintainer
  I want SSE event names recorded in a frozen inventory with a CI contract test
  So that a silent value drift cannot stop the UI from updating

  Background:
    Given the frozen SSE event-name inventory in docs/architecture/sse-event-inventory.json

  Scenario: Backend constant matches the frozen inventory
    Given the frozen SSE event-name inventory
    When the backend contract test compares constants to the inventory
    Then every constant value matches exactly

  Scenario: A renamed event is caught in CI
    Given a backend constant whose value differs from the inventory
    When the backend contract test runs
    Then the test fails and names the mismatched constant
