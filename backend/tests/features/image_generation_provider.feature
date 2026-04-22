Feature: Pluggable image generation provider and style
  As a carousel creator
  I want to pick which image model and style the pipeline uses
  So I can pair the right visual tone with my content

  Background:
    Given the carousel pipeline has reached the image-generation phase
    And the project has a resolved theme palette with primary and accent colors
    And the content LLM has returned a scene description for each slide

  # Default / happy path ---------------------------------------------------

  Scenario: Default provider + style when caller omits both fields
    Given the project does not specify an image_model or image_style
    When the pipeline renders the image-generation phase
    Then the Gemini provider is selected
    And the comic_neon style wrapper is applied
    And the final prompt includes "Comic/manga style illustration"
    And the final prompt includes the project's primary and accent hex colors

  Scenario: Caller picks OpenAI hyperreal preset
    Given the project has image_model "openai" and image_style "hyperreal"
    When the pipeline renders the image-generation phase
    Then the OpenAI provider is selected
    And the hyperreal style wrapper is applied
    And the final prompt includes "Hyperreal illustration"
    And the final prompt forbids readable text, logos, captions, and UI labels

  Scenario: Caller picks OpenAI cinematic preset
    Given the project has image_model "openai" and image_style "cinematic"
    When the pipeline renders the image-generation phase
    Then the cinematic style wrapper is applied
    And the final prompt includes "Cinematic photoreal still frame"

  Scenario: Caller picks OpenAI neo-anime preset
    Given the project has image_model "openai" and image_style "neo_anime"
    When the pipeline renders the image-generation phase
    Then the neo-anime style wrapper is applied
    And the final prompt includes "Cel-animated feature film still"

  # Validation -------------------------------------------------------------

  Scenario: Invalid model rejected at API layer
    When a caller POSTs a project with image_model "dalle-3"
    Then the API responds 422
    And the error body mentions "image_model"

  Scenario: Invalid style rejected at API layer
    When a caller POSTs a project with image_style "ukiyo_e"
    Then the API responds 422
    And the error body mentions "image_style"

  Scenario: Incompatible combo rejected
    Given the combination (gemini, cinematic) is not registered
    When a caller POSTs a project with image_model "gemini" and image_style "cinematic"
    Then the API responds 422
    And the error body mentions "not supported"

  # Failure / edge cases --------------------------------------------------

  Scenario: Missing OPENAI_API_KEY fails the pipeline with actionable message
    Given OPENAI_API_KEY is unset
    And the project has image_model "openai" and image_style "hyperreal"
    When the pipeline renders the image-generation phase
    Then the project is marked failed
    And the error_message contains "OPENAI_API_KEY"

  Scenario: OpenAI returns 403 (organization not verified) surfaces a helpful hint
    Given the OpenAI API returns a 403 verification error
    When the pipeline renders the image-generation phase
    Then the project is marked failed
    And the error_message contains "verification"

  Scenario: Style wrapper never rewrites the LLM scene description
    Given the LLM scene is "a hooded figure at a neon terminal"
    When any strategy wraps the scene
    Then the final prompt still contains that exact scene text
    And the scene appears after the style directives, not before
