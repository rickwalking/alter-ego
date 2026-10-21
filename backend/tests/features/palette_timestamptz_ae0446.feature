Feature: Palette timestamps become timezone-aware with the deploy (AE-0446, D-6)
  Prod does not run Alembic and create_all never alters a column, so the
  deploy runs an idempotent one-shot that turns palettes.created_at and
  updated_at into timestamptz. No manual ALTER on prod.

  Scenario: Naive palette timestamps are converted as UTC
    Given a Postgres palettes table whose timestamps are naive
    And a palette stored with a naive UTC time
    When the one-shot runs with --apply --verify
    Then both columns are timestamptz
    And the stored instant is unchanged, read as UTC
    And the command exits 0

  Scenario: A second run changes nothing
    Given the palette timestamps are already timestamptz
    When the one-shot runs with --apply again
    Then no column is altered

  Scenario: Verify fails while a column is still naive
    Given a Postgres palettes table whose timestamps are naive
    When the one-shot runs with --verify only
    Then the command exits 1 and names the naive columns

  Scenario: Palette creates work with naive and aware times after the change
    Given the palette timestamps are timestamptz
    When a palette is created with a naive UTC time and another with an aware one
    Then both are stored and read back as aware UTC

  Scenario: The one-shot is a no-op outside Postgres
    Given a SQLite database
    When the one-shot runs with --apply --verify
    Then it reports there is nothing to do and exits 0

  Scenario: The command needs a mode
    When the one-shot runs without --apply or --verify
    Then it exits 2 with a usage error

  Scenario: The deploy runs it after the blog cutover and never keeps the stack down
    Given the deploy workflow
    Then the one-shot runs after the blog cutover and before the stack comes up
    And its failure is captured, the stack comes up, and the job fails at the end
