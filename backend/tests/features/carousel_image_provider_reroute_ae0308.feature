Feature: Comic Neon re-routed to OpenAI and unfunded providers fail fast (AE-0308)
  As a carousel creator on a deployment where only OpenAI is funded
  I want every selectable image preset to actually generate
  So a carousel never burns research/content work and dies at the images phase

  Background:
    Given the deployment has OPENAI_API_KEY configured
    And the deployment intentionally has no GEMINI_API_KEY

  # Creation-time fail-fast guard --------------------------------------------

  Scenario: Creating a Comic Neon carousel succeeds on the OpenAI provider
    When a client POSTs a project with image_model "openai" and image_style "comic_neon"
    Then the project is created with status 201
    And the stored project has image_model "openai" and image_style "comic_neon"

  Scenario: Creation fails fast when the requested provider has no API key
    Given OPENAI_API_KEY is not configured
    When a client POSTs a project with image_model "openai" and any supported style
    Then the API responds 422 before any workflow phase runs
    And the error identifies the unconfigured image provider

  Scenario: A gemini combo is rejected as unsupported at validation time
    When a client POSTs a project with image_model "gemini" and image_style "comic_neon"
    Then the API responds 422 with an unsupported-combo error

  # Legacy data repair --------------------------------------------------------

  Scenario: Legacy pre-rename rows are normalized for future re-runs
    Given a project row with image_model "gemini-2.5-flash-preview-05-20" and image_style "neon_comic"
    When the image-provider repair script runs
    Then the row reads image_model "openai" and image_style "comic_neon"

  Scenario: Legacy gemini rows keep their style when it is supported
    Given a project row with image_model "gemini" and image_style "cinematic"
    When the image-provider repair script runs
    Then the row reads image_model "openai" and image_style "cinematic"

  Scenario: The repair script is idempotent
    Given a repaired project row with image_model "openai" and image_style "comic_neon"
    When the image-provider repair script runs again
    Then the row is unchanged
    And the script reports zero rows changed

  Scenario: Rows already on a supported OpenAI combo are never touched
    Given a project row with image_model "openai" and image_style "neo_anime"
    When the image-provider repair script runs
    Then the row is unchanged
