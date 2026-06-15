Feature: Unit of Work transaction boundary for knowledge writes
  As the knowledge bounded context
  I want a request-scoped Unit of Work that is the single commit owner
  So that knowledge writes commit exactly once and never persist partial state

  Background:
    Given a request-scoped Unit of Work wrapping the request AsyncSession
    And a knowledge service wired to commit through that Unit of Work

  Scenario: a successful create commits exactly once
    When a create document command succeeds
    Then the Unit of Work commits exactly once
    And the Unit of Work does not roll back

  Scenario: a successful ingest commits exactly once at the request boundary
    When an ingest document command succeeds
    Then the Unit of Work commits exactly once
    And the Unit of Work does not roll back

  Scenario: failed ingest rolls back
    Given a document ingest that fails during embedding
    When the command runs under the Unit of Work
    Then no partial document or chunks are persisted
    And the Unit of Work rolls back
    And the Unit of Work does not commit
    And the original error propagates to the caller

  Scenario: a failed delete rolls back with no partial writes
    Given a document delete that fails during vector deletion
    When the command runs under the Unit of Work
    Then the Unit of Work rolls back
    And the Unit of Work does not commit

  Scenario: the SQLAlchemy Unit of Work delegates to the wrapped session
    When the Unit of Work commits
    Then the wrapped AsyncSession is committed
    When the Unit of Work rolls back
    Then the wrapped AsyncSession is rolled back

  Scenario: the context manager commits on clean exit and rolls back on error
    When the Unit of Work context exits cleanly
    Then the wrapped session is committed and not rolled back
    When the Unit of Work context exits with an exception
    Then the wrapped session is rolled back and not committed
