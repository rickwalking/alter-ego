Feature: The carousel archived_at column reaches prod with the deploy (Pedro's decision)
  Prod does not run Alembic and create_all never adds a column to an existing
  table, so the deploy runs an idempotent one-shot that adds
  carousel_projects.archived_at and its index. No manual ALTER on prod.

  Scenario: The column and its index are added once
    Given a Postgres carousel_projects table without archived_at
    When the one-shot runs with --apply --verify
    Then archived_at exists as a nullable timestamptz with its index
    And existing carousels keep their data and are not archived
    And the command exits 0

  Scenario: A second run changes nothing
    Given carousel_projects already has archived_at and its index
    When the one-shot runs with --apply again
    Then it reports nothing was added

  Scenario: Verify fails while the column is missing
    Given a Postgres carousel_projects table without archived_at
    When the one-shot runs with --verify only
    Then the command exits 1 and names what is missing

  Scenario: The archived_at one-shot is a no-op outside Postgres
    Given a SQLite database
    When the one-shot runs with --apply --verify
    Then it reports there is nothing to do and exits 0

  Scenario: The archived_at command needs a mode
    When the one-shot runs without --apply or --verify
    Then it exits 2 with a usage error

  Scenario: The deploy adds archived_at before the stack comes up and never keeps it down
    Given the deploy workflow
    Then the one-shot runs after the palette step and before the stack comes up
    And its failure is captured, the stack comes up, and the job fails at the end
