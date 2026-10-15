Feature: GrokBot carousel defaults (AE-0361)
  Every carousel GrokBot creates has a target audience and a niche in simple
  words, a brief that covers the selected theme, and image guidance. The
  backend always uses the OpenAI image model and the auto palette theme. The
  scout picks the image preset (flat_editorial by default since AE-0372) and may send guidance
  with a theme-specific background; otherwise the backend builds it.

  Background:
    Given the signals bundle served URL A

  Scenario: Default flat_editorial style and template guidance
    When the scout posts a topic with no image_style and no image_guidance
    Then the candidate is stored with image_style "flat_editorial" and no guidance
    And the runner builds the guidance "Clean visuals that follow the chosen image style. Background: ai-themed setting."

  Scenario: Neo anime style gets the anime template guidance
    Given a stored topic with image_style "neo_anime", niche "ai" and no guidance
    When the runner builds the project spec
    Then the guidance is "Futuristic anime in the style of Akira, Ghost in the Shell and Neon Genesis Evangelion. Background: ai-themed setting."

  Scenario: Non-anime style gets style-neutral template guidance
    Given a stored topic with image_style "flat_editorial", niche "benchmarks" and no guidance
    When the runner builds the project spec
    Then the guidance is "Clean visuals that follow the chosen image style. Background: benchmarks-themed setting."

  Scenario: A bot-chosen style is accepted
    When the scout posts a topic with image_style "hyperreal" and guidance "Product photo. Background: a chip fab clean room."
    Then the candidate is stored with image_style "hyperreal" and that guidance
    And one run is queued

  Scenario: An unsupported style rejects only that topic
    When the scout posts one topic with image_style "watercolor" and one valid topic with image_style "cinematic"
    Then the response status is 200
    And only the first topic is rejected with reason "image_style_unsupported"
    And the valid topic is queued

  Scenario: An image_style longer than 40 characters fails the batch
    When the scout posts a topic whose image_style is 41 characters long
    Then the response status is 422
    And no candidate is stored

  Scenario: Image guidance over 400 characters fails the batch
    When the scout posts a topic whose image_guidance is 401 characters long
    Then the response status is 422
    And no candidate is stored

  Scenario: A URL in the image guidance is rejected
    When the scout posts a topic whose image_guidance contains a URL
    Then that topic is rejected with reason "url_in_text"

  Scenario Outline: Audience or niche that is not simple is rejected
    When the scout posts one topic whose <field> is "<value>" and one valid topic
    Then only the first topic is rejected with reason "<reason>"
    And the valid topic is queued

    Examples:
      | field    | value                                   | reason              |
      | audience | Brazilian developers who build AI tools | audience_not_simple |
      | niche    | AI agents for enterprise workflows      | niche_not_simple    |

  Scenario: A brief that misses the theme is rejected
    When the scout posts a topic titled "GPU prices crash" whose brief only talks about cooking recipes
    Then that topic is rejected with reason "brief_off_theme"

  Scenario: A brief longer than 600 characters is rejected
    When the scout posts a topic whose brief is 601 characters long
    Then the response status is 200
    And that topic is rejected with reason "brief_not_simple"

  Scenario: A brief longer than 800 characters fails the batch
    When the scout posts a topic whose brief is 801 characters long
    Then the response status is 422
    And no candidate is stored

  Scenario: The create-project call receives openai, auto, the style and the guidance
    Given a project spec with image_style "cinematic" and guidance "Cinematic still. Background: a parliament hall."
    When the editorial driver creates the carousel
    Then the carousel row has image_model "openai", theme "auto", image_style "cinematic"
    And its custom_visual_details is that guidance

  Scenario: The owner review message shows audience, niche and style
    Given the carousel has audience "developers", niche "AI agents" and image_style "neo_anime"
    When the owner review message is sent
    Then the keyboard message starts with "Audience: developers · Niche: AI agents · Style: neo_anime"
