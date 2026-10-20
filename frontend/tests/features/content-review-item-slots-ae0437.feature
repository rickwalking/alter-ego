Feature: The content review can add and remove structured items and always save edits (AE-0437)

  Prod QA 2026-10-19, carousel 7acaf967: the closing slide had "actions: []"
  and the manual editor showed "Campo estruturado: actions []" with no way to
  add an action, so the owner was stuck until a revision produced them.
  Carousel 5344b6c6: a late-added EN TL;DR edit could not be saved because
  "Enviar correções manuais" only showed while the server was blocking.

  Scenario: A closing slide without actions offers an "add action" slot
    Given an editable closing slide whose PT and EN "actions" are empty
    When the content review renders it
    Then no "Structured field: actions" extra is shown
    And each column offers "Add Action"

  Scenario: Adding an action creates an empty slot in PT and EN
    Given an editable closing slide whose PT and EN "actions" are empty
    When the reviewer clicks "Add Action" in the PT column
    Then PT and EN each have 1 action with an icon and empty title and body
    And the action fields are editable

  Scenario: Removing an item removes the same position in PT and EN
    Given an editable summary slide with 3 points in PT and EN
    When the reviewer removes point 2 in the EN column
    Then PT and EN each keep points 1 and 3

  Scenario: A list is capped at 4 items
    Given an editable content slide with 4 features
    Then no "Add Feature" button is shown

  Scenario: A closing slide edits its actions, not a stray features list
    Given an editable closing slide whose PT has 3 actions and EN has 3 features
    When the content review renders the EN column
    Then the EN column edits "actions" (mirrored from PT)

  Scenario: Unsaved edits can be submitted when the server is not blocking
    Given a content review whose server validation is not blocking
    When the reviewer edits the EN TL;DR
    Then "Submit manual fixes" is shown and enabled
    And no blocking-slides hint is shown

  Scenario: Nothing to submit hides the button when nothing blocks
    Given a content review whose server validation is not blocking
    And the reviewer has not edited anything
    Then "Submit manual fixes" is not shown
