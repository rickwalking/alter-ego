Feature: "Ponto de Vista" prompts, hook candidates and rubric (AE-0375, ADR-0021)
  The model may sharpen the owner's thesis but never invent their opinion,
  experiences, test results or numbers.

  # --- Prompts ----------------------------------------------------------------

  Scenario: Every POV prompt carries the never-invent rule
    When the POV hook, outline, content and caption prompts are rendered
    Then each tells the model never to invent experiences or numbers

  Scenario: No proof means no anecdotes
    Given a POV project without personal proof
    When the content prompt renders
    Then it tells the model to argue from reasoning, never with an invented story

  Scenario: The outline prompt lists the contract roles in order
    Given a 9-slide POV project
    When the outline prompt renders
    Then it asks for exactly 9 slides with roles hook, rehook, pov, point, point, point, twist, save, cta

  # --- Outline phase ------------------------------------------------------------

  Scenario: Hook candidates on the outline
    Given a POV project with a thesis
    When the outline phase runs
    Then slide 1 carries the hook candidates and its title is the first candidate
    And every slide has the role of its position, whatever the model returned

  Scenario: A failed hook call keeps the outline
    Given the hook candidate call fails
    When the outline phase runs
    Then the outline is kept with an empty candidate list

  Scenario: The owner's saved hook wins
    Given a POV project whose owner saved a hook
    When the outline phase runs again
    Then slide 1's title is the saved hook

  Scenario Outline: Thesis on slides 1-2 outline check
    Given a POV outline whose first two slides <mention> the thesis
    When the outline checks run
    Then thesis_early is <result>

    Examples:
      | mention         | result |
      | mention         | true   |
      | do not mention  | false  |

  Scenario: Radar IA v4 outline is sized and stamped
    Given a Radar IA project stamped hero_lower_third_v4 with 8 slides
    When the outline phase runs
    Then the outline agent is asked for 8 slides and the roles are stamped by position

  Scenario: Legacy projects keep the legacy outline
    Given a project stamped hero_lower_third_v3
    When the outline phase runs
    Then the outline agent is called exactly as before

  # --- Hook pick ------------------------------------------------------------------

  Scenario: Owner picks a hook
    Given a POV carousel
    When the owner saves the hook "Pare de pedir código pra IA"
    Then the hook is stored and the content phase drafts slide 1 with it

  Scenario: Hook too long
    When the owner saves a hook of 12 words
    Then the API answers 422

  Scenario: Hook on a legacy carousel
    Given a carousel stamped hero_lower_third_v3
    When the owner saves a hook
    Then the API answers 409

  # --- Content and caption -------------------------------------------------------

  Scenario: POV slides are drafted with the POV prompt
    Given a POV project
    When slide 1 is drafted
    Then the carousel_pov content prompt is used with the hook, the thesis and the role

  Scenario: POV caption
    Given a POV project with cta_goal "send"
    When the caption prompt is built
    Then it renders carousel_pov caption with the slide 1 hook, the thesis and the goal

  # --- Rubric ----------------------------------------------------------------------

  Scenario: Hook word limit fires
    Given a POV deck whose slide 1 heading has 11 words
    When the deck is validated
    Then hook_word_limit is reported as a blocker

  Scenario: First person warning
    Given a POV deck with only 2 first-person slides
    When the deck is validated
    Then first_person_missing is reported as a warning and does not block

  Scenario: Radar IA v4 decks do not get the POV rules
    Given a Radar IA v4 deck with an 11-word hook and no first person
    When the deck is validated
    Then neither hook_word_limit nor first_person_missing is reported
