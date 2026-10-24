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
