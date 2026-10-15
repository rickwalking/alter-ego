Feature: Create wizard content mode (AE-0373, ADR-0021)
  The backend scenarios live in backend/tests/features/carousel_content_mode.feature.

  Scenario: Radar IA is the default mode
    Given the create wizard opens
    Then "Radar IA" is selected and the POV inputs are hidden
    And the six Radar IA templates are shown

  Scenario: Switching to Ponto de Vista
    When the owner selects "Ponto de Vista"
    Then the thesis, proof, slide count and CTA goal inputs are shown
    And the four POV formats replace the templates
    And the template selection resets to the first format

  Scenario: Thesis is required in POV
    Given the wizard is in "Ponto de Vista" mode with a blank thesis
    Then the thesis-required note is shown
    And "Start Carousel" is disabled

  Scenario: POV request carries the POV fields
    Given a POV form with a thesis, the "Como eu faço" format, 10 slides and the "send" goal
    When the create request is built
    Then it carries content_mode "pov", the trimmed thesis, pov_format "como_eu_faco", slide_count 10 and cta_goal "send"

  Scenario: Radar IA request carries no POV fields
    Given a Radar IA form with a leftover thesis
    When the create request is built
    Then it carries content_mode "news_analysis" and no thesis

  Scenario: The "Pedro" persona is preselected
    Given the persona list has "Pedro"
    When the wizard loads
    Then "Pedro" is the selected persona

  Scenario: No "Pedro" persona
    Given the persona list has no "Pedro"
    When the wizard loads
    Then no persona is selected

  # PR #106 review (AE-0371): the slide-1 photo is required for POV.
  Scenario: POV submit needs the slide-1 photo
    Given the wizard in "Ponto de Vista" mode with a thesis
    And no slide-1 photo is selected
    Then "Start Carousel" is disabled

  Scenario: POV create sends the chosen photo
    Given the wizard in "Ponto de Vista" mode with a thesis and a selected photo
    When the owner starts the carousel
    Then the create request carries hook_asset_id with the photo id
    And no separate hook-photo call is made after the project is created

  Scenario: Radar IA create never sends a photo
    Given the wizard in "Radar IA" mode with a photo left selected
    When the owner starts the carousel
    Then the create request has no hook_asset_id
