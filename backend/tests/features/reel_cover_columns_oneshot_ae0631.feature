Feature: The reel cover columns reach prod with the deploy (AE-0631)
  Prod does not run Alembic, and create_all never adds a column to an existing
  table. Revision c3d4e5f6a7b9 adds purpose and repost_id to the existing
  autopilot_cover_assets table, so the deploy runs an idempotent one-shot that
  adds them before the stack comes up.

  Scenario: The reel cover columns are added once
    Given a Postgres autopilot_cover_assets table without purpose and repost_id
    When the one-shot runs with --apply --verify
    Then purpose exists as a NOT NULL varchar that reads "carousel_cover" on existing rows
    And repost_id exists as a nullable uuid
    And the command exits 0

  Scenario: A second reel cover columns run changes nothing
    Given autopilot_cover_assets already has purpose and repost_id
    When the one-shot runs with --apply again
    Then it reports nothing was added

  Scenario: Verify fails while a reel cover column is missing
    Given a Postgres autopilot_cover_assets table without purpose and repost_id
    When the one-shot runs with --verify only
    Then the command exits 1 and names the missing columns

  Scenario: A database without the cover table is left alone
    Given a Postgres database without autopilot_cover_assets
    When the one-shot runs with --apply --verify
    Then it reports there is no table yet and exits 0

  Scenario: The reel cover columns one-shot is a no-op outside Postgres
    Given a SQLite database
    When the one-shot runs with --apply --verify
    Then it reports there is nothing to do and exits 0

  Scenario: The reel cover columns one-shot matches the ORM columns
    Given the cover asset ORM model
    Then purpose is a NOT NULL 16-char string defaulting to "carousel_cover" and repost_id a nullable uuid
    And the command needs a mode to run

  Scenario: The deploy adds the reel cover columns without keeping the stack down
    Given the deploy workflow
    Then the one-shot runs after the token version step and before the stack comes up
    And its failure is captured, the stack stays up, and the job fails at the end
