Feature: Provide image guidance when creating a carousel (AE-0298)
  The Topic & Brief step offers an optional free-text image-guidance input
  that feeds the backend custom_visual_details field (already wired into
  every slide image prompt via _compose_scene).

  Scenario: Guidance is sent to the backend
    Given the admin fills the image guidance field in the Topic & Brief step
    When they submit the create carousel form
    Then the POST /carousels payload includes custom_visual_details with the trimmed text

  Scenario: Blank guidance sends null
    Given the admin leaves the image guidance field empty (or whitespace)
    When they submit the create carousel form
    Then custom_visual_details is null in the payload

  Scenario: Over-length guidance is rejected before submit
    Given the admin attempts more than 500 characters of image guidance
    Then the input caps at 500 characters
    And the Zod request schema rejects a >500-char value

  Scenario: Guidance round-trips through the project response
    Given a carousel created with image guidance
    When the project is reloaded
    Then the response echoes custom_visual_details
    And the frontend schema accepts the echoed field

  Scenario: Guidance reaches the slide image prompts after the brand lock
    Given a project with custom_visual_details
    When the image prompt package is rendered (backend unit)
    Then the guidance appears in a "Visual direction:" clause after the locked directives
