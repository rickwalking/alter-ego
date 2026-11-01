Feature: A boost without a Meta Page fails before any Marketing API call
  Meta needs a Facebook Page and the Instagram user id to boost an Instagram post.
  When either id is empty the launch stops at once with the permanent error
  meta_page_missing, and the request is stored as failed with that code.

  Scenario: An empty Page id fails the launch before any Meta call
    Given the ads gateway is enabled and the Page id is empty
    When an approved boost is launched
    Then the launch fails with the permanent error meta_page_missing
    And no Marketing API request is made

  Scenario: An empty Instagram user id fails the launch before any Meta call
    Given the ads gateway is enabled and the Instagram user id is blank
    When an approved boost is launched
    Then the launch fails with the permanent error meta_page_missing
    And no Marketing API request is made

  Scenario: The worker stores the boost as failed with meta_page_missing
    Given an approved boost request and an ads gateway without a Page id
    When the worker ticks with spending enabled
    Then the request is stored as failed with error code meta_page_missing

  Scenario: A configured Page still reaches the Marketing API
    Given the ads gateway is enabled with a Page id and an Instagram user id
    When an approved boost is launched
    Then the preflight and the paused creates are sent to Meta and the ad is activated

  Scenario: The kill switch wins over a missing Page
    Given the ads gateway is disabled and the Page id is empty
    When an approved boost is launched
    Then the launch fails with ads_disabled and no Marketing API request is made
