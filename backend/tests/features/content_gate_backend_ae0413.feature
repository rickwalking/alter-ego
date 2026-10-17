Feature: Content gate manual fixes, feedback history, LLM input case and research relevance (AE-0413)
  QA run 2026-10-16 (REPORT B02, B03, B12, B14, B16). "Submit manual fixes" was
  rejected on the first content gate and, once accepted, regenerated and
  re-translated the slides instead of keeping the edits. Content notes looked
  lost, the copy came back lowercase, and Russian search hits reached the blog.

  # --- B02: manual fixes on the first content gate ------------------------------

  Scenario: Manual fixes are accepted on the first content gate
    Given a carousel workflow that went research -> outline -> content
    And no content revision has run yet
    When the structured-feedback guard reads the checkpoint phase
    Then the phase is "content"
    And edited localized slides are allowed

  Scenario: The parked content checkpoint names the content gate
    Given the graph parked at the first content review
    Then the stored current_phase is "content", not "outline"

  Scenario: The approved-hold park keeps the final_review phase
    Given an approved carousel parked at the approved hold
    When the structured-feedback guard reads the checkpoint phase
    Then the phase is "final_review"

  # --- B03: manual fixes apply the edits and re-validate only -------------------

  Scenario: Manual fixes on the first content gate keep the edited copy without regenerating
    Given a carousel workflow parked at the first content review
    When the reviewer submits manual fixes for slide 2 with no feedback
    Then the content ensure does not run again and the drafting model is not called
    And slide 2's PT and EN copy is the edited copy byte-for-byte
    And every other slide keeps its localized copy unchanged
    And the validation report is rebuilt from the edited slides

  Scenario: A manual fix followed by approval commits the edited copy
    Given the reviewer submitted manual fixes for slide 2
    When the reviewer approves the content
    Then the drafting model is not called
    And slide 2 keeps the edited copy at the design phase

  Scenario: A content re-entry without regeneration keeps the stored EN translations
    Given stored EN translations for the drafts
    When the content ensure runs without new notes
    Then the EN copy comes from the stored translations, not from the PT draft

  Scenario: Portuguese EN copy is reported on every content result
    Given an EN heading "Agentes de código mudam o review"
    When the slide is validated
    Then a wrong_language violation is reported for the EN heading
    And a v3 policy reports it as translation_not_english

  # --- B16: content notes reach the model and are recorded ----------------------

  Scenario: A consumed content note is exposed in the state response
    Given a content note was applied by a regeneration
    When the workflow state is served
    Then phase_feedback.content is empty
    And phase_feedback_history.content holds the note with status "applied"

  Scenario: The fail-closed re-draft carries the reviewer notes
    Given a content regeneration with the note "EN em inglês"
    When a blocking slide is re-drafted once
    Then the re-draft receives the note "EN em inglês"

  # --- B12: LLM inputs keep their case ------------------------------------------

  Scenario: Topic, brief and feedback keep their case on the way to the LLM
    Given the topic "Agentes de código em times pequenos com GLM"
    When it is sanitized for the LLM
    Then the case is preserved
    And injection phrases are still removed case-insensitively

  Scenario: The sentence-case marker message does not claim an auto-capitalization
    Given a slide whose copy the model wrote in lowercase
    When the slide is validated
    Then the message asks to edit or regenerate the slide
    And it does not say the text was auto-capitalized

  # --- B14: research sources are PT/EN and on topic -----------------------------

  Scenario: A bracketed tag prefix is not part of the search query
    Given the topic "[QA 2026-10-16] Agentes de código em times pequenos 🤖"
    When the topic is searched
    Then the query is "Agentes de código em times pequenos"

  Scenario: Foreign-language and off-topic search hits are discarded
    Given search hits in Russian, an off-topic English hit and two relevant hits
    When the research sources are enriched
    Then only the relevant Portuguese and English hits are kept
    And a discarded hit does not use a slot of the search cap

  Scenario: Owner-provided sources are kept whatever their language
    Given an owner-provided source written in Russian
    When the research sources are enriched
    Then the owner source is kept unchanged
