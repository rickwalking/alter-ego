Feature: A request's database session closes with the request
  Every route that depends on get_db holds one session. The session and its
  connection must be released when the request ends, however it ends, and not
  whenever the garbage collector next runs.

  Scenario: A handler that succeeds releases its connection
    Given a route that reads through get_db
    When the request succeeds
    Then no connection is checked out when the response has returned

  Scenario: A handler that refuses the request releases its connection
    Given a route that reads through get_db and then raises an HTTP error
    When the request is refused
    Then no connection is checked out when the response has returned

  Scenario: A handler that crashes releases its connection
    Given a route that reads through get_db and then raises an unexpected error
    When the request fails with a server error
    Then no connection is checked out when the response has returned

  Scenario: A refused request leaves nothing for the garbage collector
    Given a route that reads through get_db and then raises an HTTP error
    When the request is refused and the engine is disposed straight after
    Then no connection is deleted before being closed

  Scenario: The session is closed when the dependency is thrown into
    Given a session handed out by get_db
    When the dependency receives the handler's exception
    Then the session has released its connection before the exception returns
