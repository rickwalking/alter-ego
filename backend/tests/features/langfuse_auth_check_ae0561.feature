Feature: Langfuse startup credentials are verified without delaying the application
  The web application and generation worker diagnose invalid Langfuse configuration
  through one bounded background check while startup and tracing remain best-effort.

  Scenario: Valid Langfuse credentials log success without delaying startup
    Given Langfuse is configured and its public projects request blocks briefly
    When shared observability initialization returns before that request completes
    Then the check finishes asynchronously and logs one langfuse_auth_ok with a credential-free host

  Scenario: Rejected Langfuse credentials log an authentication failure
    Given a client whose public projects response is empty or raises a 401 response error
    When the background credential check runs
    Then it logs one langfuse_auth_failed warning with a status code or exception type
    And the application keeps the tracing client and callback handler available

  Scenario: A timed out credential check logs unreachable
    Given a client whose public projects request exceeds the configured deadline
    When the background credential check times out
    Then it logs one langfuse_auth_unreachable warning with the timeout exception type
    And a late completion does not log another outcome

  Scenario: A credential check exception is contained without secrets
    Given a client whose auth check raises an exception containing planted credentials
    When the background credential check runs
    Then it logs one safe warning with only the host and exception type
    And no key, authorization header, credential-bearing URL, response body, traceback, or exception message is logged

  Scenario: Diagnostic hosts contain only credential-free origins
    Given configured hosts with userinfo, an IPv6 origin, an unsupported scheme, or a malformed port
    When their diagnostic host is derived
    Then only the safe HTTP(S) origin is retained or a fixed redacted placeholder is returned
