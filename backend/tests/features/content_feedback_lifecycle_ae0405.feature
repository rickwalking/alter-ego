Feature: Content revision notes are consumed by the regeneration that uses them (AE-0405)
  A content revision note steers exactly one regeneration. Once the content
  node regenerates with it, the note leaves the active notes and is kept in a
  history for the audit and the persona feedback loop. A resubmit or resume
  that carries no new feedback never regenerates the slide copy, even when
  older notes exist. Autopilot gate feedback is tagged and never re-fed.

  The content node re-runs on every resume (LangGraph replays the interrupted
  node), so the artifacts the reviewer saw are written to the checkpoint when
  the graph parks at the content review, and the replay reuses them.

  Background:
    Given a carousel workflow parked at the content review
    And the drafting model is a fake (no network)

  # --- Happy path -----------------------------------------------------------

  Scenario: A feedback revise regenerates once and moves the note to history
    When the reviewer revises the content with the note "Tighten the thesis"
    Then the drafting model is called once with the note "Tighten the thesis"
    And the active content notes are empty
    And the content feedback history holds "Tighten the thesis" with status "applied" and source "human"

  Scenario: Approving after a feedback revise keeps the reviewed drafts
    Given the reviewer revised the content with the note "Tighten the thesis"
    When the reviewer approves the content
    Then the drafting model is not called again
    And the committed drafts are the drafts the reviewer approved

  # --- Edits-only -----------------------------------------------------------

  Scenario: An edits-only resubmit after a feedback revise keeps the edited copy
    Given the reviewer revised the content with the note "Tighten the thesis"
    When the reviewer submits manual fixes for slide 2 with no feedback
    Then the drafting model is not called again
    And slide 2's localized copy is the edited copy byte-for-byte

  Scenario: A new note after an edits-only resubmit regenerates with only that note
    Given the reviewer revised the content with the note "Tighten the thesis"
    And the reviewer submitted manual fixes for slide 2 with no feedback
    When the reviewer revises the content with the note "Shorter hook"
    Then the drafting model is called with only the note "Shorter hook"

  # --- Autopilot ------------------------------------------------------------

  Scenario: Autopilot gate feedback is tagged, applied once and not re-fed
    When the autopilot revises the content with "persona_score_below_threshold. Measured: 5.8"
    Then the note is stored with source "autopilot"
    And the drafting model is called once with that note
    And the content feedback history holds the note with status "applied" and source "autopilot"
    And a later edits-only resubmit does not call the drafting model

  Scenario: An active autopilot note is dropped when the content gate passes
    Given an autopilot note that no regeneration used
    When the content is approved
    Then the autopilot note is in the history with status "dropped"
    And the active content notes are empty

  # --- Approval resume ------------------------------------------------------

  Scenario: The resume on approval does not regenerate without unapplied notes
    Given hand-fixed slides 3 and 8 in the checkpoint
    When the reviewer approves the content
    Then the drafting model is not called
    And slides 3 and 8 keep the hand-fixed copy

  # --- Migration of existing state ------------------------------------------

  Scenario: Legacy notes that predate the last regeneration move to history
    Given a legacy checkpoint with three untagged content notes and drafts
    When any review resumes the workflow
    Then the three notes are in the history with status "migrated"
    And the active content notes are empty

  Scenario: Legacy notes of a failed regeneration stay active
    Given a legacy checkpoint with an untagged content note
    And the content phase failed
    When the workflow resumes
    Then the note stays active for the retry

  # --- Failures -------------------------------------------------------------

  Scenario: A regeneration that fails keeps the note active
    Given the drafting model returns invalid JSON
    When the content node regenerates with the note "Tighten the thesis"
    Then the phase is marked failed
    And the note "Tighten the thesis" is still active

  Scenario: The feedback history is queryable per phase
    Given notes applied, dropped and migrated on the content phase
    When the persona feedback loop reads the content history
    Then it gets each note with its source, status and timestamps
    And malformed history entries are skipped
