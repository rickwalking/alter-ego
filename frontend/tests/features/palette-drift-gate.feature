Feature: Palette-drift contract gate (AE-0266 Phase 3, retargeted by AE-0271)
  As the carousel maintainer
  I want the frontend's still-static IMAGE_PRESETS checked against the backend
  palette contract (docs/contracts/palettes.json)
  So that the provider/style matrix can never silently desync from the backend.

  # AE-0271 made the theme dropdown render the live GET /api/palettes catalog
  # (roots + custom), so the hardcoded CAROUSEL_THEMES / THEME_LABEL_KEYS /
  # LIGHT_THEME_KEYS / i18n theme labels no longer exist — a static gate can't
  # check a runtime list. The gate narrows to the IMAGE_PRESETS surface, which
  # is provider-tied and stays hardcoded in the frontend.

  Background:
    Given the backend emits docs/contracts/palettes.json from the palette registry
    And the gate is "node scripts/check-palette-drift.mjs --strict"

  Scenario: In-sync tree passes
    Given src/constants/create.ts IMAGE_PRESETS match the contract image_presets
    When the gate runs
    Then it exits 0

  Scenario: A missing image preset combo fails
    Given the contract declares a (model, style) preset absent from IMAGE_PRESETS
    When the gate runs
    Then it exits non-zero reporting the missing preset

  Scenario: An unexpected image preset combo fails
    Given IMAGE_PRESETS declares a (model, style) combo absent from the contract
    When the gate runs
    Then it exits non-zero reporting the unexpected preset
