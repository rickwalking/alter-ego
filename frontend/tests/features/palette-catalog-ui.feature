Feature: Dynamic palette catalog in the dashboard (AE-0271)
  As an authenticated creator
  I want to browse, create, edit, and archive custom palettes, and pick any of
  them (plus the roots) when creating a carousel
  So that the catalog is editable at runtime and the create flow never depends on
  a hardcoded theme list (ADR-0019; co-deploys with the AE-0270 API, G6).

  Background:
    Given the palette_catalog feature flag is enabled
    And I am an authenticated user

  Scenario: A newly created custom palette appears in the create dropdown
    Given a custom palette "Aurora" was created via the catalog
    When I open the create page
    Then "Aurora" appears in the theme dropdown alongside the root palettes

  Scenario: Image style is shown as derived, not chosen
    Given I open the palette create form
    When I set the mode to "light"
    Then the form shows the image style as "Flat Editorial" and read-only

  Scenario: A light palette nudges the create preset
    Given the catalog includes a light custom palette
    When I select it as the carousel theme
    Then the image preset switches to the flat-editorial preset

  Scenario: Root palettes are read-only in the catalog
    When I view the palette catalog
    Then root palettes show a "root" badge and no edit or archive action

  Scenario: Creating rejects an invalid colour before submit
    When I enter a colour that is not a #rrggbb hex value
    Then the create button is disabled and an inline error is shown

  Scenario: A duplicate name surfaces the server conflict inline
    Given a custom palette named "Aurora" already exists
    When I create another palette named "Aurora"
    Then the form shows a duplicate-name error and no palette is created

  Scenario: Archiving a custom palette removes it from the catalog
    Given a custom palette "Aurora" exists
    When I archive it and confirm
    Then it disappears from the catalog

  Scenario: Empty custom catalog shows only roots with a create prompt
    Given no custom palettes have been created yet
    When I open the palette catalog
    Then the root palettes are shown
    And an empty-state prompt invites creating the first custom palette
