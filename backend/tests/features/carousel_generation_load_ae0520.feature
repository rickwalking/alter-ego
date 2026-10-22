Feature: Carousel generation does not take the website down (Pedro's decision)
  The morning autopilot batch and interactive runs share one 2 vCPU / 3.8 GB box
  with the website. Exports run one at a time, CPU-heavy image work runs off the
  event loop, autopilot starts are spaced, and the phase index reaches prod with
  an idempotent deploy one-shot.

  Scenario: Two carousels exporting at the same time run one Chromium export at a time
    Given two carousels reach export at the same time
    When both export their slides
    Then only one Chromium export runs at any moment
    And both exports finish with their slides

  Scenario: An export that fails releases the slot for the next one
    Given an export whose Chromium launch fails
    When a second export waits for the slot
    Then the second export runs after the first one failed

  Scenario: Exports in different processes wait on the Postgres advisory lock
    Given a Postgres database
    And another session holds the export advisory lock
    When an export asks for the slot
    Then it waits until that session releases the lock

  Scenario: The exporter launches Chromium with the low-memory flags
    When a carousel is exported
    Then Chromium is launched with --disable-dev-shm-usage and --renderer-process-limit=1

  Scenario: Image cropping and the PDF build run off the event loop
    Given an export runs
    When the slides are cropped, the artwork optimized and the PDF built
    Then each of those calls runs in a worker thread, not on the event loop

  Scenario: A queued run waits until the previous start is 20 minutes old
    Given a run started 5 minutes ago
    When the runner steps a queued run
    Then the queued run stays queued and no carousel is created

  Scenario: Three runs queued at 11:05 start at least 20 minutes apart
    Given three runs are queued at 11:05
    When the runner steps every minute and each run leaves generating quickly
    Then the generation starts are at least 20 minutes apart

  Scenario: Spacing 0 starts queued runs back to back
    Given the start spacing is 0 minutes
    And a run started a minute ago
    When the runner steps a queued run
    Then the queued run starts

  Scenario: A run whose start failed retries without waiting for itself
    Given a queued run whose carousel was created but whose start failed
    When the runner steps it again
    Then it retries the start without waiting for the spacing

  Scenario: The latest start is the newest carousel created by another run
    Given two autopilot runs with carousels created at 11:05 and 11:25
    When the start history is read excluding the second run
    Then the latest start is 11:05
    And with no other run attached to a carousel there is no latest start

  Scenario: The phase index one-shot creates the index once
    Given a Postgres carousel_projects table without the phase index
    When the one-shot runs with --apply --verify twice
    Then the index exists once and is valid
    And the second run creates nothing

  Scenario: An invalid leftover phase index is rebuilt
    Given an invalid phase index left by a failed concurrent build
    When the one-shot runs with --apply --verify
    Then the index is dropped and built again, valid

  Scenario: Verify fails while the phase index is missing
    Given a Postgres carousel_projects table without the phase index
    When the one-shot runs with --verify only
    Then the command exits 1

  Scenario: The phase index one-shot is a no-op outside Postgres
    Given a SQLite database
    When the one-shot runs with --apply --verify
    Then it reports there is nothing to do and exits 0

  Scenario: The phase index command needs a mode
    When the one-shot runs without --apply or --verify
    Then it exits 2 with a usage error

  Scenario: The deploy runs the phase index after the palette step and never keeps the stack down
    Given the deploy workflow
    Then the one-shot runs after the palette timestamptz step and before the stack comes up
    And a failure fails the job only after the stack is up
