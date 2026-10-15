Feature: Radar IA quick fixes (AE-0372, growth plan 16.4 #3-#7)
  As the account owner
  I want Portuguese slides, short captions and a specific call to action
  So that each carousel reads as mine and asks for one clear action

  # --- Swipe hint ------------------------------------------------------------

  Scenario: Portuguese swipe hint
    Given a PT carousel intro slide
    When it is rendered
    Then the footer shows "Deslize →"

  Scenario: English swipe hint stays English
    Given an EN carousel intro slide
    When it is rendered
    Then the footer shows "Swipe →"

  # --- Slide counter ---------------------------------------------------------

  Scenario Outline: Slide counter is zero-padded to two digits
    Given a <total>-slide carousel
    When slide <number> is rendered
    Then the counter reads "<counter>"

    Examples:
      | total | number | counter |
      | 7     | 3      | 03 / 07 |
      | 10    | 10     | 10 / 10 |
      | 10    | 9      | 09 / 10 |

  Scenario: A missing slide number falls back to slide 1
    Given a CTA slide without a number in a 7-slide carousel
    When it is rendered
    Then the counter reads "01 / 07"

  # --- Caption v7 ------------------------------------------------------------

  Scenario: Caption v7 keeps hashtags short and the CTA single
    Given a carousel with slide headings
    When the caption prompt is built
    Then the prompt comes from carousel/v7/caption_prompt
    And it asks for 3 to 5 hashtags and a single call to action
    And it puts the slide 1 hook on the first line
    And it never asks for "Salve" and "Compartilhe" together

  # --- CTA slide copy --------------------------------------------------------

  Scenario: CTA slide uses the follow variant in Portuguese
    Given a PT Radar IA carousel by "@pedromarins.ai"
    When the CTA slide is rendered
    Then it shows "Siga @pedromarins.ai: toda terça e quinta eu traduzo IA em decisões reais."
    And it no longer shows "Siga para mais conteúdo como esse"

  Scenario: CTA slide uses the follow variant in English
    Given an EN Radar IA carousel by "@pedromarins.ai"
    When the CTA slide is rendered
    Then it shows "Follow @pedromarins.ai: every Tuesday and Thursday I turn AI into real decisions."

  # --- Image defaults --------------------------------------------------------

  Scenario: Missing image style falls back to flat editorial
    Given a create request without an image style
    When the project is created
    Then its image style is "flat_editorial"

  Scenario: The autopilot defaults to flat editorial
    Given a scout topic without an image style
    When the autopilot builds the project spec
    Then the image style is "flat_editorial"
