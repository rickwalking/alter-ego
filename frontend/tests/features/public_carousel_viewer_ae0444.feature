# language: en
@AE-0444 @frontend @public
Feature: Public carousel slide viewer
  A visitor can step through a published carousel with buttons, the keyboard,
  or touch, and switch content language when both translations exist.

  Scenario: The viewer starts on the first slide
    Given a published carousel with several slides
    When a visitor opens its viewer
    Then slide 1 is visible
    And the counter says "Slide 1 of N"

  Scenario: Next and previous buttons move one slide
    Given the viewer is open
    When the visitor clicks next
    Then slide 2 is visible
    When the visitor clicks previous
    Then slide 1 is visible

  Scenario: Arrow keys move one slide
    Given the carousel region has focus
    When the visitor presses ArrowRight
    Then the next slide is visible
    When the visitor presses ArrowLeft
    Then the previous slide is visible

  Scenario: The first and last slides do not wrap with buttons
    Given the viewer is on slide 1
    Then the previous button is disabled
    Given the viewer is on the last slide
    Then the next button is disabled

  Scenario: Dots jump to a slide
    Given the viewer is open
    When the visitor clicks the dot for slide 3
    Then slide 3 is visible
    And that dot is marked as current

  Scenario: Swiping moves one slide
    Given the viewer is open
    When the visitor swipes left
    Then the next slide is visible
    When the visitor swipes right
    Then the previous slide is visible

  Scenario: The language toggle appears only when both languages exist
    Given a carousel with Portuguese and English slides
    Then the PT/EN toggle is visible
    Given a carousel with only Portuguese slides
    Then the PT/EN toggle is not visible

  Scenario: Switching language swaps the slide images
    Given the viewer is showing Portuguese slides
    When the visitor selects English
    Then the English slide image is shown

  Scenario: Private or unknown carousels are 404
    Given an unknown or private carousel id
    When a visitor opens its viewer
    Then the page returns not found
