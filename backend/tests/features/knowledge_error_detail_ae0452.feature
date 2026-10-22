# language: en
@AE-0452 @backend
Feature: Knowledge failures are logged, not echoed to the client
  A failed search or document ingest is a server error. The client gets a
  fixed message; the exception (which can carry vector-store hosts, keys or
  parser internals) goes to the server log only.

  Scenario: A failed search answers a fixed 500 and logs the error
    Given the knowledge search backend fails with an internal error
    When an editor searches the knowledge base
    Then the response is a 500 with the fixed "search failed" message
    And the internal error text is not in the response
    And the failure is logged with its exception

  Scenario: A failed document ingest answers a fixed 500 and logs the error
    Given document ingestion fails with an internal error
    When an editor uploads a valid text file
    Then the response is a 500 with the fixed "document processing failed" message
    And the internal error text is not in the response
    And the failure is logged with its exception

