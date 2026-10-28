Feature: The generation queue schema one-shot resolves the events foreign keys
  The deploy runs the queue schema one-shot in a bare process that loads no
  other model, so the events table must still find carousel_projects.

  Scenario: The events DDL compiles in a process that loaded no other model
    Given a fresh Python process that imports only the queue schema module
    When it compiles the generation events DDL for Postgres
    Then the DDL references carousel_projects and generation_runs with ON DELETE CASCADE

  Scenario: Apply and verify on a fresh database exit 0
    Given a Postgres schema holding carousel_projects and generation_runs only
    When the one-shot runs with --apply --verify
    Then it exits 0 and carousel_generation_events exists with its indexes

  Scenario: A second apply and verify is a no-op that exits 0
    Given the one-shot already applied the queue schema
    When it runs with --apply --verify again
    Then it exits 0 and nothing is reported missing

  Scenario: Verify fails when the events table is missing
    Given a Postgres schema with no carousel_generation_events table
    When the one-shot runs with --verify only
    Then it exits 1 and reports carousel_generation_events missing
