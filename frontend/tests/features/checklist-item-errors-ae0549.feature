Feature: Checklist rule errors show where the owner fixes them
  A too-short summary list used to be reported on the slide body, so the owner
  looked for the error in the wrong place.

  Scenario: An incomplete summary point is flagged on that item
    Given summary_points_missing is reported on summary_points[1].body
    When the content review renders the slide
    Then the second item is marked invalid with the message under it, and the slide body is not

  Scenario: A too-short summary list is flagged under the items heading
    Given summary_points_missing is reported on summary_points
    When the content review renders the slide, with one item or none
    Then the message shows under the items heading

  Scenario: Adding an item clears the list error
    Given a list-level error on summary_points
    When the owner adds an item
    Then the list error is cleared in both locales
