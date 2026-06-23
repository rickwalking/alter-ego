Feature: Palette-drift contract gate (AE-0266 Phase 3)
  As the carousel maintainer
  I want the frontend theme dropdown, zod presets, and i18n labels checked
  against the backend palette contract (docs/contracts/palettes.json)
  So that adding a palette stays one backend registry row and the UI can never
  silently desync (the "FE missed a new theme" class of the AE-0264 bugs).

  Background:
    Given the backend emits docs/contracts/palettes.json from the palette registry
    And the gate is "node scripts/check-palette-drift.mjs --strict"

  Scenario: In-sync tree passes
    Given src/constants/create.ts and the i18n locales match the contract
    When the gate runs
    Then it exits 0

  Scenario: A new contract theme missing from the dropdown fails
    Given the contract declares a theme absent from CAROUSEL_THEMES
    When the gate runs
    Then it exits non-zero reporting the missing theme

  Scenario: A diverging i18n label fails
    Given an en/pt label differs from the contract label for a theme
    When the gate runs
    Then it exits non-zero reporting the i18n mismatch

  Scenario: A missing image preset combo fails
    Given the contract declares a (model, style) preset absent from IMAGE_PRESETS
    When the gate runs
    Then it exits non-zero reporting the missing preset

  Scenario: A light theme missing from LIGHT_THEME_KEYS fails
    Given a contract light theme is absent from LIGHT_THEME_KEYS
    When the gate runs
    Then it exits non-zero so the light-on-dark nudge cannot be skipped
