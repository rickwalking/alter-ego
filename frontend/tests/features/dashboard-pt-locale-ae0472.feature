Feature: The dashboard speaks Portuguese when the interface is Portuguese
  As the site owner using the dashboard in Portuguese
  I want every label, list and legend in Portuguese
  So that I do not read a mix of English and Portuguese

  Scenario: The dashboard overview is fully translated
    Given the interface language is Portuguese
    When I open the dashboard overview
    Then the quick actions, the activity lists and the breadcrumb are in Portuguese
    And no English quick-action, activity or breadcrumb text is shown

  Scenario: The analytics breadcrumb is translated
    Given the interface language is Portuguese
    When I open the editorial analytics
    Then the breadcrumb is in Portuguese

  Scenario: The calendar legend, chips and empty month are translated
    Given the interface language is Portuguese
    When the content calendar shows a month with and without items
    Then the legend, the content-type and status chips and the empty-month message are in Portuguese

  Scenario: Activity counts use the singular for one item
    Given the interface language is Portuguese
    When the dashboard activity lists show a count of one
    Then the item and weekly-velocity counts read "1 item" and "1 post/semana"
