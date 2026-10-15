Feature: Autopilot "Ponto de Vista" topics and the owner's thesis (AE-0377, ADR-0021)
  The scout may propose a POV topic with a DRAFT thesis. Nothing is generated
  until the owner confirms it, replaces it with their own, or discards it.

  # --- Intake (scout v3) ---------------------------------------------------------

  Scenario: A v2 proposal is Radar IA
    Given a scout proposal without a mode
    When it is planned
    Then it is stored as news_analysis exactly as before

  Scenario: POV without a draft thesis
    Given a POV proposal without thesis_draft
    When it is planned
    Then it is rejected with thesis_missing

  Scenario: Second Radar IA run in the same week
    Given a news_analysis run created this São Paulo week
    When another news_analysis proposal arrives
    Then it is rejected with weekly_news_cap_reached

  Scenario: Only one Radar IA run is queued per week
    Given two news_analysis proposals in one batch and room for two runs
    When the batch is planned
    Then only the best-scored one is queued and POV proposals are not capped

  Scenario: A draft thesis with a URL is rejected
    Given a POV proposal whose thesis contains a URL
    When it is planned
    Then it is rejected with url_in_text

  # --- Runner ------------------------------------------------------------------------

  Scenario: A v3 batch carries a Radar IA topic and a POV topic with a thesis
    Given the v3 routine pack example
    When it is posted to /api/autopilot/topics
    Then both topics are queued: one news_analysis and one pov with its draft thesis

  Scenario: A POV run waits for the thesis
    Given a queued POV run without a confirmed thesis
    When the runner ticks
    Then the run moves to awaiting_thesis and no carousel is created

  Scenario: A confirmed POV run starts generating
    Given a queued POV run with a confirmed thesis
    When the runner ticks
    Then a POV carousel is created with the owner's thesis and the pov_editorial preset

  Scenario: Unanswered thesis expires
    Given a run waiting for its thesis for more than 72 hours
    When the sweep runs
    Then the run is expired

  # --- Telegram ------------------------------------------------------------------------

  Scenario: The owner is asked once
    Given a run awaiting its thesis
    When the Telegram tick runs twice
    Then exactly one prompt with Confirmar, Editar and Descartar is sent

  Scenario: Owner confirms the draft thesis
    Given a POV run with a draft thesis
    When the owner taps Confirmar
    Then the thesis is stored and the run is queued for generation

  Scenario: Double tap confirms once
    When the owner taps Confirmar twice
    Then the second tap answers that the thesis was already resolved

  Scenario: Owner edits the thesis
    When the owner taps Editar and replies with a new thesis
    Then the run is queued with the owner's text

  Scenario: Edited thesis too long
    When the owner replies with more than 280 characters
    Then the owner is asked again and the run keeps waiting

  Scenario: Owner discards
    When the owner taps Descartar
    Then the run is rejected and nothing is generated

  Scenario: A non-owner taps a thesis button
    When someone else taps Confirmar
    Then nothing changes

  # --- POV publish slots (R6 glue for AE-0370) ------------------------------------------

  Scenario Outline: Next POV slot
    Given it is <now> in São Paulo
    When the next POV slot is computed
    Then it is <slot>

    Examples:
      | now                  | slot                 |
      | Tuesday 11:30        | Tuesday 12:00        |
      | Tuesday 11:50        | Thursday 12:00       |
      | Thursday 12:00       | next Tuesday 12:00   |
      | Saturday 09:00       | next Tuesday 12:00   |

  # --- POV slots wired into AE-0370's publish choice (R6) --------------------------------

  Scenario: next_slot mode schedules a POV run for Tuesday or Thursday at noon
    Given AUTOPILOT_DEFAULT_PUBLISH is next_slot
    And a POV run with a confirmed thesis awaits the owner on Thursday 13:00
    When the owner taps Approve
    Then the run is scheduled for next Tuesday 12:00

  Scenario: The Agendar menu lists the POV slot first
    Given a POV run with a confirmed thesis awaits the owner on Thursday 13:00
    When the owner taps Agendar
    Then the slots are next Tuesday 12:00, today 18:00 and today 21:00

  Scenario: A Radar IA run keeps the default slots
    Given a Radar IA run awaits the owner on Thursday 13:00
    When the owner taps Agendar
    Then the slots are today 18:00, today 21:00 and tomorrow 12:00
