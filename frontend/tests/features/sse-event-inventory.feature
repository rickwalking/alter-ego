Feature: SSE event names are frozen during the migration
  As a platform maintainer
  I want the frontend SSE event-name maps verified against the frozen inventory
  So that a value drift cannot silently stop the UI from updating

  Background:
    Given the frozen SSE event-name inventory in docs/architecture/sse-event-inventory.json

  Scenario: Frontend constants match the inventory
    Given the frontend EDITORIAL_WORKFLOW_SSE_EVENTS constants map
    When the frontend contract test compares its values to the inventory
    Then every frontend constant value exists in the inventory

  Scenario: Drifted frontend constant is caught in CI
    Given a frontend event-name constant whose value differs from the inventory
    When the frontend contract test runs
    Then the test fails and names the mismatched constant
