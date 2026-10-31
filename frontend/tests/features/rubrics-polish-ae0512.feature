@AE-0512 @frontend
Feature: The rubrics page reads well in both languages, on a phone and from the keyboard
  The rubric list shows what the API returns, translated: every content type a
  rubric applies to, each criterion's real weight, and whether the rubric is the
  default. Nothing on the card is made up. The card fits a 390 px screen, its
  actions are large enough to tap and reachable by keyboard, and the inline
  editor asks for confirmation in its own dialog before discarding changes.

  Background:
    Given the API returns a default rubric for carousels and blog posts
    And its criteria use the "0-100", "1-10", "pass_fail" and "grade_a_f" scales

  Scenario: The rubric list is fully translated
    When the owner opens the rubrics page in Portuguese
    Then the threshold cells read "Atinge o limite" and "Abaixo do limite"
    And no cell reads "Meets threshold" or "Below threshold"
    And the scales read "0–100", "1–10", "Aprovado / reprovado" and "Nota A–F"
    And no raw scale key such as "pass_fail" or "grade_a_f" is shown

  Scenario: Scale ranges use an en dash
    When the owner opens the rubrics page in English
    Then a 1-10 criterion with threshold 0.8 reads "≥ 80% (1–10)"
    And the "Poor" column header reads "Poor (1–2)"

  Scenario: The card shows every content type the rubric applies to
    When the owner opens the rubrics page
    Then the default rubric's card shows both "Carousel" and "Blog post"

  Scenario: The card shows only the data the API returns
    When the owner opens the rubrics page
    Then each criterion shows its own weight from the API
    And the default rubric is marked "Default"
    And no card shows a made-up rubric weight or an "active" status

  Scenario: The card fits a 390 px screen with tappable actions
    Given a 390 px wide screen
    When the owner opens the rubrics page
    Then the card header wraps instead of clipping its actions
    And Edit and Delete are at least 44 px tall and wide
    And the criteria stack instead of needing a horizontal scroll

  Scenario: Discarding unsaved changes asks in an in-app dialog
    Given the owner edited a rubric without saving
    When the owner presses Cancel
    Then a modal dialog asks whether to leave without saving
    And focus moves into the dialog
    And choosing to keep editing closes it and returns focus to Cancel
    And choosing to leave closes the editor without saving

  Scenario: Escape cancels the editor
    Given the rubric editor is open with no changes
    When the owner presses Escape
    Then the editor closes and the list is shown

  Scenario: Escape on a changed editor goes through the dialog
    Given the owner edited a rubric without saving
    When the owner presses Escape
    Then the leave dialog opens and the editor stays open
    And pressing Escape again closes only the dialog

  Scenario: Each row's actions are reachable by Tab in order
    Given two rubrics, one of them the default
    When the owner tabs through the list
    Then focus reaches each rubric's Edit then Delete in list order
    And each focused action shows a visible focus ring
