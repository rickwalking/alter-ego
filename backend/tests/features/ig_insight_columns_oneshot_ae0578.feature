Feature: The Instagram insight columns reach prod with the deploy
  Prod does not run Alembic and create_all never adds a column to an existing
  table, so the deploy runs an idempotent one-shot that adds the four nullable
  insight columns to instagram_post_insights. Once the stack is up (so the
  app's create_all has made any new table), it checks that no mapped ORM
  column is missing from the live database.

  Scenario: The four insight columns are added once
    Given a Postgres instagram_post_insights table without the insight columns
    When the one-shot runs with --apply --verify
    Then likes, comments, avg_watch_time_ms and total_watch_time_ms exist as nullable integers
    And existing insight rows keep their data
    And the command exits 0

  Scenario: A second insight columns run changes nothing
    Given instagram_post_insights already has the insight columns
    When the one-shot runs with --apply again
    Then it reports nothing was added

  Scenario: Verify fails while an insight column is missing
    Given a Postgres instagram_post_insights table without the insight columns
    When the one-shot runs with --verify only
    Then the command exits 1 and names the missing columns

  Scenario: A database without the insights table is left alone
    Given a Postgres database without instagram_post_insights
    When the one-shot runs with --apply --verify
    Then it reports there is no table yet and exits 0

  Scenario: The insight columns one-shot is a no-op outside Postgres
    Given a SQLite database
    When the one-shot runs with --apply --verify
    Then it reports there is nothing to do and exits 0

  Scenario: The insight columns command needs a mode
    When the one-shot runs without --apply or --verify
    Then it exits 2 with a usage error

  Scenario: The one-shot adds exactly the columns the ORM maps
    Given the instagram post insights ORM model
    Then every column the one-shot adds is a nullable integer the model maps

  Scenario: The deploy adds the insight columns and checks drift without keeping the stack down
    Given the deploy workflow
    Then the one-shot runs after the generation queue schema step and before the stack comes up
    And the schema drift check runs in the running backend after the stack comes up, with retries
    And each failure is captured, the stack stays up, and the job fails at the end
