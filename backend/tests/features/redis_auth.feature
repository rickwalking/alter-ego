Feature: redis requires authentication in production (AE-0302)
  Production Redis holds carousel checkpoints, workflow state, and the Redis
  Streams event log. Every client must authenticate; missing credentials fail
  closed on BOTH sides (backend ConfigError, Redis container refuses to start).

  Scenario: unauthenticated access is rejected
    Given Redis is configured with requirepass in production
    When a client issues a command without authenticating
    Then Redis returns a NOAUTH error

  Scenario: missing password fails closed on the server side too
    Given ENVIRONMENT is production and REDIS_PASSWORD is empty or unset
    When the Redis container starts
    Then it refuses to start (exits non-zero / unhealthy)
    And it does NOT run as an open, unauthenticated instance

  Scenario: the backend authenticates successfully
    Given the backend is configured with the Redis password from the environment
    When it publishes a workflow event to Redis Streams
    Then the command succeeds and the event is recorded

  Scenario: missing credential fails fast
    Given the Redis password env var is unset
    When the backend builds its Redis client in a production-like environment
    Then it raises a clear configuration error rather than connecting unauthenticated

  Scenario: unset or unrecognized ENVIRONMENT fails closed
    Given ENVIRONMENT is unset or carries an unrecognized value
    And no Redis credential is configured
    When the backend builds its Redis client
    Then it requires authentication (raises a configuration error)

  Scenario: explicit development environment tolerates an absent password
    Given ENVIRONMENT is development or test
    And no Redis credential is configured
    When the backend builds its Redis client
    Then it connects without authentication (local/CI path)

  Scenario: conflicting credentials fail closed
    Given REDIS_URL embeds a password and REDIS_PASSWORD is set to a different value
    When the backend builds its Redis client in a production-like environment
    Then it raises a configuration error rather than silently picking one

  Scenario: a direct Redis construction outside the factory is caught
    Given a backend module constructs redis.Redis directly instead of using the factory
    When the factory-enforcement checker runs
    Then it exits non-zero naming the violating file
