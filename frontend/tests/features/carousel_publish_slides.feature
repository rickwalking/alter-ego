Feature: Carousel Publish Slide Images
  As a content creator
  I want to see composed slides in the publish panel
  So that I can preview the final carousel with text overlay

  Background:
    Given a completed carousel project exists

  Scenario: Publish panel shows composed slides for new projects
    Given the project has rendered_slides_pt in design_tokens
    When I open the publish panel
    Then the carousel viewer should show composed slide images
    And the slides should have text overlay

  Scenario: Publish panel shows composed slides for legacy projects
    Given the project was created before rendered_slides existed
    And the composed slides exist on disk
    When I open the publish panel
    Then the carousel viewer should show composed slide images
    And the slides should have text overlay

  Scenario: Publish panel switches between PT and EN composed slides
    Given the project has both rendered_slides_pt and rendered_slides_en
    When I select the Portuguese language tab
    Then the carousel viewer should show Portuguese composed slides
    When I select the English language tab
    Then the carousel viewer should show English composed slides

  Scenario: Download PDF works correctly
    Given I am on the publish panel
    When I click download PDF
    Then the PDF should contain composed slides with text overlay
