Feature: Carousel content mode and POV inputs (AE-0373, ADR-0021)
  As the account owner
  I want to choose between "Radar IA" and "Ponto de Vista" when I create a carousel
  So that a POV carousel is built from my own thesis and proof

  # --- Defaults --------------------------------------------------------------

  Scenario: Default mode is Radar IA
    Given a create request without content_mode
    When it is submitted
    Then the project is created with content_mode "news_analysis"
    And its POV fields are empty

  Scenario: Existing rows read as Radar IA
    Given a stored project whose content_mode is NULL
    When it is read through the API
    Then content_mode is "news_analysis"

  # --- POV happy path --------------------------------------------------------

  Scenario: POV project with all fields
    Given a pov create request with thesis "A IA escreve código. Quem decide ainda é você."
    And personal proof, format "opiniao", 9 slides and cta_goal "send"
    When it is submitted
    Then the response carries the same POV fields

  Scenario: POV defaults
    Given a pov create request with only a thesis
    When it is submitted
    Then the format is "opiniao", the slide count is 9 and the CTA goal is "follow"

  Scenario: Thesis is trimmed
    Given a pov create request whose thesis has surrounding spaces
    When it is submitted
    Then the stored thesis has no surrounding spaces

  # --- POV failures ----------------------------------------------------------

  Scenario: POV without thesis
    Given a pov create request with a blank thesis
    When it is submitted
    Then the API answers 422

  Scenario: POV thesis too long
    Given a pov create request with a 281-character thesis
    When it is submitted
    Then the API answers 422

  Scenario Outline: POV slide count out of range
    Given a pov create request with <slides> slides
    When it is submitted
    Then the API answers 422

    Examples:
      | slides |
      | 7      |
      | 11     |

  Scenario: Unknown POV format
    Given a pov create request with format "listicle"
    When it is submitted
    Then the API answers 422

  Scenario: Unknown content mode
    Given a create request with content_mode "reels"
    When it is submitted
    Then the API answers 422

  # --- Radar IA guards -------------------------------------------------------

  Scenario: POV fields on a Radar IA request
    Given a news_analysis create request with a thesis
    When it is submitted
    Then the API answers 422

  Scenario: Radar IA with the optional eighth slide
    Given a news_analysis create request with 8 slides
    When it is submitted
    Then the project stores slide_count 8

  Scenario: Unknown CTA goal
    Given a create request with cta_goal "dance"
    When it is submitted
    Then the API answers 422

  # --- Persona and template --------------------------------------------------

  Scenario: Persona and template are persisted
    Given an existing persona and a create request with that persona and strategy "feature_grid"
    When it is submitted
    Then the project stores the persona id and slide_layout_strategy "feature_grid"

  Scenario: Unknown persona
    Given a create request with a persona id that does not exist
    When it is submitted
    Then the API answers 404 and nothing is created

  Scenario: Workflow start uses the project's persona
    Given a project created with a persona
    When the workflow starts without a persona id
    Then the project's persona voices and scores the carousel

  # --- Wizard ----------------------------------------------------------------

  Scenario: Wizard POV mode
    Given the create wizard in "Ponto de Vista" mode
    Then it requires the thesis and shows proof, format, slide count and CTA goal
    And the template list shows only the four POV formats

  Scenario: Wizard Radar IA mode
    Given the create wizard in "Radar IA" mode
    Then the POV fields are hidden and the six Radar IA templates are shown

  # --- Idempotent migrations (PR #106 review, item 2) -------------------------

  Scenario: Fresh upgrade adds the AE-0371 schema
    Given a database stamped before the AE-0371 revisions
    When alembic upgrades to head
    Then the POV columns, the creator-asset role/pose and instagram_post_insights exist

  Scenario: Re-running the AE-0371 migrations on a database that already has them
    Given a database whose AE-0371 columns and table were applied by hand
    And alembic believes it is before the AE-0371 revisions
    When alembic upgrades to head twice
    Then no error is raised and the schema is unchanged

  Scenario: Downgrading over objects that are already gone
    Given a database whose AE-0371 columns and table were already dropped
    When alembic downgrades the AE-0371 revisions again
    Then no error is raised

  # --- Slide-1 photo on create (PR #106 review, item 4) -----------------------

  Scenario: POV create needs the slide-1 photo
    Given a POV create request without hook_asset_id
    When it is submitted
    Then the API answers 422 "hook_asset_id is required when content_mode is 'pov'"

  Scenario: POV create binds and stages the chosen photo
    Given a POV create request with one of the owner's hook photos
    When it is submitted
    Then the project stores hook_asset_id and the photo is staged in its output folder

  Scenario: POV create with an unknown photo creates nothing
    Given a POV create request whose hook_asset_id does not exist
    When it is submitted
    Then the API answers 400 "creator_asset_not_found" and no project is created

  Scenario: POV create with another user's photo
    Given a POV create request with another user's photo
    When it is submitted
    Then the API answers 403

  Scenario: Radar IA rejects a slide-1 photo
    Given a Radar IA create request with hook_asset_id
    When it is submitted
    Then the API answers 422
