Feature: Republish a completed carousel's artifacts
  A completed, already-versioned carousel can be re-rendered from its persisted
  slide data and atomically re-activated as a new content-addressed artifact
  version, so slide fixes made after completion propagate into the served PDF
  without operator access.

  Background:
    Given a completed carousel with an active artifact version

  Scenario: Republish after a slide text fix
    And its slide copy was corrected after completion
    When the user clicks "Rebuild PDF" on the publish page
    Then slides and PDFs re-render from the persisted slide data
    And a new artifact version is built and activated
    And the downloaded PDF contains the corrected copy

  Scenario: Health check validates fresh outputs, not the old version root
    When the republish pipeline health-checks the re-rendered outputs
    Then it validates the files the render just wrote under the project root
    And it does not report the fresh PDFs as missing

  Scenario: Failed republish never corrupts a completed project
    When the republish pipeline fails during artifact build
    Then the project status remains completed
    And the previously active artifact version keeps serving
    And the project error_message is left untouched

  Scenario: Republish with unchanged content is a safe no-op
    Given a completed carousel republished moments ago
    When the user clicks "Rebuild PDF" again
    Then the existing content digest is re-activated without error
    And current.json still names the re-activated version immediately

  Scenario: Concurrent republishes serialize on the build lock
    Given two republish requests arrive for the same project concurrently
    When both reach the artifact build
    Then the second is rejected by the per-project build lock as build_in_progress
    And current.json reflects exactly one coherent activation

  Scenario: Republish is refused while a workflow run is active
    Given the completed carousel has an in-progress workflow run
    When the user requests a republish
    Then the request is refused with a run_in_progress conflict
