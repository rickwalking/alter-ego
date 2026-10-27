Feature: Langfuse startup credentials are verified without delaying the application
  The web application and generation worker diagnose invalid Langfuse configuration
  through one bounded background check while startup and tracing remain best-effort.

  Scenario: Valid Langfuse credentials log success without delaying startup
    Given Langfuse is configured and its credential check blocks briefly
    When shared observability initialization returns before that check completes
    Then the check finishes asynchronously and logs one langfuse_auth_ok with the host

  Scenario: Rejected Langfuse credentials log an authentication failure
    Given a client whose auth check returns false or raises a 401 response error
    When the background credential check runs
    Then it logs one langfuse_auth_failed warning with a status code or exception type
    And the application keeps the tracing client available

  Scenario: A timed out credential check logs unreachable
    Given a client whose auth check exceeds the configured deadline
    When the background credential check times out
    Then it logs one langfuse_auth_unreachable warning with the timeout exception type
    And a late completion does not log another outcome

  Scenario: A credential check exception is contained without secrets
    Given a client whose auth check raises an exception containing planted credentials
    When the background credential check runs
    Then it logs one safe warning with only the host and exception type
    And no key, authorization header, credential-bearing URL, response body, traceback, or exception message is logged
