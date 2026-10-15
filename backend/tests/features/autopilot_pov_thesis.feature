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

  # --- POV approve in "now" mode (PR #106 review, item 5) ---------------------

  Scenario Outline: A POV approve in "now" mode is scheduled for the next Tue/Thu noon
    Given AUTOPILOT_DEFAULT_PUBLISH is "now" and a POV run awaiting the owner
    When the owner taps Aprovar at <approved_at> São Paulo time
    Then the run is scheduled for <slot> São Paulo time and nothing is released

    Examples:
      | approved_at          | slot                 |
      | Monday 09:00         | Tuesday 12:00        |
      | Tuesday 11:50        | Thursday 12:00       |
      | Thursday 13:00       | next Tuesday 12:00   |

  Scenario: A Radar IA approve in "now" mode still publishes now
    Given AUTOPILOT_DEFAULT_PUBLISH is "now" and a Radar IA run awaiting the owner
    When the owner taps Aprovar
    Then the publish-now / schedule choice is shown and nothing is scheduled
    And "Publicar agora" approves and releases the carousel immediately

  # --- Persona and voice gate (PR #106 review, item 3) ------------------------

  Scenario: The autopilot persona comes from AUTOPILOT_PERSONA_ID
    Given AUTOPILOT_PERSONA_ID names an existing persona
    When a queued run builds its carousel spec
    Then the spec, the created carousel and the workflow start carry that persona

  Scenario Outline: An empty or unknown AUTOPILOT_PERSONA_ID falls back to "Pedro"
    Given AUTOPILOT_PERSONA_ID is <configured> and a persona named "pedro" exists
    When the persona is resolved
    Then the "pedro" persona is used

    Examples:
      | configured      |
      | empty           |
      | blank           |
      | not-a-persona   |

  Scenario: No persona at all is recorded, not invented
    Given AUTOPILOT_PERSONA_ID is empty and no persona is named "Pedro"
    When a Radar IA run starts
    Then it starts with no persona and a "persona unresolved" warning is logged

  Scenario: An unscored POV carousel escalates
    Given a POV run at the content gate with no voice score
    When the policy decides
    Then the run escalates at once with reason "persona_not_scored"
    And Telegram says "POV precisa da persona Pedro configurada"

  Scenario: An unscored Radar IA carousel keeps AE-0364
    Given a Radar IA run at the content gate with no voice score
    When the policy decides
    Then the content gate is approved

  Scenario: A scored POV carousel follows the voice floor
    Given a POV run at the content gate with a voice score below 70
    When the policy decides
    Then the content gate is revised for "persona_score_below_threshold"

  # --- Slide-1 photo (PR #106 review, item 4) ---------------------------------

  Scenario: The most recently used hook photo opens the POV deck
    Given the owner has two hook photos and used the older one on a carousel
    When a POV run creates its carousel
    Then the older photo is bound and staged where the slides render

  Scenario: Without a used photo the newest hook photo is picked
    Given the owner has hook photos but none was used yet
    When a POV run creates its carousel
    Then the newest hook photo is bound (cta photos are ignored)

  Scenario: An unreadable hook photo counts as missing
    Given the newest hook photo's stored file is gone
    When the slide-1 photo is chosen
    Then the next readable photo is used, or none when no file is left

  Scenario: No hook photo, no POV run
    Given a confirmed POV run and an owner with no usable hook photo
    When the runner ticks
    Then no carousel is created and the run fails with reason "hook_photo_missing"
    And Telegram asks the owner to upload a hook photo in the dashboard

  # --- Scout POV format (PR #106 review, item 6) ------------------------------

  Scenario: The scout chooses the format and the slide count of a POV topic
    Given a scout v3 POV topic with pov_format "erros_e_mitos" and slide_count 8
    When the intake accepts it and the run starts
    Then the carousel is created with format "erros_e_mitos" and 8 slides

  Scenario: Defaults apply only when the scout chose nothing
    Given a scout v3 POV topic without pov_format and slide_count
    When the run starts
    Then the carousel uses DEFAULT_POV_FORMAT "opiniao" and 9 slides

  Scenario: A Radar IA topic ignores a POV choice
    Given a Radar IA topic that carries pov_format and slide_count
    When the intake accepts it
    Then neither is stored

  Scenario Outline: An invalid POV choice rejects the batch
    Given a scout v3 POV topic with <choice>
    When the batch is posted
    Then the API answers 422 and nothing is stored

    Examples:
      | choice                 |
      | pov_format "listicle"  |
      | slide_count 7          |
      | slide_count 11         |
