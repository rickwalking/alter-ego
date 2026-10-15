Feature: Radar IA quick fixes in the create wizard (AE-0372)
  The backend scenarios live in backend/tests/features/radar_ia_quick_fixes.feature.

  Scenario: Missing image style falls back to flat editorial
    Given the create form has no image preset
    When the create request is built
    Then the image model is "openai" and the image style is "flat_editorial"

  Scenario: Unknown preset falls back to flat editorial
    Given the create form has an unknown image preset
    When the create request is built
    Then the image style is "flat_editorial"

  Scenario: Explicit preset is kept
    Given the owner picked the Comic Neon preset
    When the create request is built
    Then the image style is "comic_neon"
