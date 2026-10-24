Feature: The slide editor edits exactly the text each slide shows
  As the owner editing a carousel's slide text
  I want every structured item field I edit to be the one the slide displays
  So that my edits to a checklist slide appear on the slide

  Scenario: A checklist slide edits one line per item
    Given a slide the workflow state lists as a checklist slide
    When the owner opens the slide editor on the publish page or at content review
    Then each item shows a single "Checklist line" field holding the text on the slide
    And an item without a title shows its body, as the slide does

  Scenario: Editing a checklist line writes the displayed field
    Given a checklist slide item
    When the owner edits its line in Portuguese or in English
    Then the edit sets the item title and empties the hidden body in that language

  Scenario: Grid and list slides edit the title and the body
    Given a slide whose layout shows each item's title and body
    When the owner opens the slide editor
    Then each item shows a title field and a body field, both editable

  Scenario: Slides that are not listed stay title-and-body
    Given a workflow state that lists no checklist slides
    When the slides are resolved for editing
    Then no slide is marked as a checklist slide

  Scenario: The checklist editor offers the lines the slide draws
    Given a checklist slide whose lists hold blank items, more than five items, or several lists
    When the owner opens the slide editor on the publish page
    Then it offers the first list with a line, in the template's order (summary points, actions, features)
    And it drops blank items and offers at most five lines, as the slide does

  Scenario: An edit made in the editor is saved and rendered
    Given the slide the backend serves for generated checklist content
    When the owner edits a checklist line in Portuguese and in English
    Then the editor sends the payload the backend saves and renders with the edited lines

  Scenario: A start response or a live update keeps the checklist slides
    Given the editor holds the checklist slides of the workflow state
    When a workflow event that does not carry them arrives
    Then the checklist slides are kept
