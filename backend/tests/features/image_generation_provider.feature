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
    Then the OpenAI provider is selected
    And the neo_anime style wrapper is applied
    And the final prompt includes the project's primary and accent hex colors

  Scenario: Caller picks OpenAI comic-neon preset (AE-0308 re-route)
    Given the project has image_model "openai" and image_style "comic_neon"
    When the pipeline renders the image-generation phase
    Then the OpenAI provider is selected
    And the comic_neon style wrapper is applied
    And the final prompt includes "Comic/manga style illustration"
    And the final prompt includes the project's primary and accent hex colors
    And the final prompt forbids real-world brand names and celebrity likenesses
    And the prompt is otherwise byte-identical to the pre-AE-0308 Gemini-era prompt

  Scenario: No Gemini combo remains supported (AE-0308)
    Given prod intentionally has no GEMINI_API_KEY
    When any (gemini, style) combo is validated against the supported combos
    Then the combo is rejected as unsupported
    And the provider registry raises for image_model "gemini"

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

  Scenario: Caller picks OpenAI flat-editorial preset for a light palette
    Given the project has image_model "openai" and image_style "flat_editorial"
    And the project has a resolved LIGHT theme palette
    When the pipeline renders the image-generation phase
    Then the flat-editorial style wrapper is applied
    And the final prompt includes "Flat editorial vector illustration"
    And the final prompt includes "Light background"
    And the final prompt does not mention "neon glow"

  # Palette selection -----------------------------------------------------

  Scenario: A light palette is reachable only by explicit selection
    Given a project with theme "paper_editorial"
    When the theme is resolved
    Then the resolved palette is the light paper_editorial palette

  Scenario: AUTO never assigns a light palette to a dark strategy
    Given a project with theme AUTO and no matching brand or category keywords
    When the theme is resolved for many different topics
    Then the resolved palette is never one of the light palettes

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

  # Custom visual details + revision (AE-0263 / AE-0261) ---------------------

  Scenario: Project custom visual details reach every slide image prompt
    Given a project with custom_visual_details "Rio de Janeiro skyline at golden hour"
    When slide image prompts are rendered
    Then each rendered prompt contains "Visual direction: Rio de Janeiro skyline"

  Scenario: No custom visual details leaves the scene unchanged
    Given a project with no custom_visual_details
    When a slide image prompt is rendered
    Then the rendered prompt does not contain "Visual direction:"

  Scenario: Image revision feedback changes the rendered prompt
    Given an image phase awaiting human review
    When the user requests an image revision with feedback
    Then the feedback is appended to the project custom_visual_details
      And the regenerated prompt hash differs from the previous one

  # NSFW / non-humanoid safety clause (AE-0328) -------------------------------

  Scenario: Every rendered slide prompt carries the safety clause
    Given any supported image model and style combo
    When a slide image prompt is rendered
    Then the rendered prompt ends the scene with the SAFETY clause
      And the clause forbids nudity and demands modest, fully clothed people
      And the clause forces abstract or AI entities to be non-humanoid

  Scenario: Steering custom visual details cannot escape the safety clause
    Given a project with custom_visual_details "Ghost in the Shell style female hologram"
    When a slide image prompt is rendered
    Then the rendered prompt still contains the SAFETY clause
      And the clause appears after the user's visual direction

  Scenario: Revision feedback rebuilds still carry the safety clause
    Given revision feedback appended to the project custom_visual_details
    When the slide image prompt is re-rendered
    Then the rendered prompt still contains the SAFETY clause
