Feature: QA follow-ups from the 2026-10-16 run, backend (AE-0416)
  The PT blog body is Portuguese from its first line, and the workflow board
  keeps rejected projects out of the phase columns.

  # --- Blog composition (PT body started with an English paragraph) ---

  Scenario: The PT blog body never carries the English research intro
    Given a carousel whose research summary is "Researchers found that the model leaked."
    And its slides carry Portuguese long-form notes
    When the PT blog markdown is built
    Then it starts with the title followed by the first section heading
    And it does not contain "Researchers found that the model leaked."

  Scenario: The EN blog body keeps the research intro
    Given the same carousel with English translations of its notes
    When the EN blog markdown is built
    Then the research summary is the first paragraph after the title

  Scenario: The editorial distribution build passes research only to EN
    Given a distribution build with a research summary
    When the PT and EN bodies are stored on the project
    Then the PT body has no research paragraph
    And the EN body has it

  Scenario: An empty research summary leaves the EN body without an intro
    Given a carousel with no research summary
    When the EN blog markdown is built
    Then the title is followed directly by the first section heading

  # --- Workflow board (rejected cards were grouped under "Brief") ---

  Scenario: A rejected project goes to the Rejected column
    Given a project at phase "brief" whose phase status is "rejected"
    When the workflow board is projected
    Then the "rejected" column holds the card
    And the "brief" column does not

  Scenario: A project rejected at a later phase keeps that phase on its card
    Given a project at phase "content" whose phase status is "rejected"
    When the workflow board is projected
    Then the card is in the "rejected" column
    And the card's current phase is "content"

  Scenario: The Rejected column is the last column
    When the workflow board is projected
    Then the columns are the eight workflow phases followed by "rejected"

  Scenario: Non-rejected projects stay in their phase column
    Given a project at phase "content" whose phase status is "awaiting_human"
    When the workflow board is projected
    Then the card is in the "content" column
    And the "rejected" column is empty
