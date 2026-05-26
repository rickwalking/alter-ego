Feature: Admin Re-render Missing Slides
  As an admin
  I want to re-render missing PT/EN slide images for completed carousels
  So that carousels generated before Playwright was installed have all slides

  Background:
    Given I am authenticated as an admin

  Scenario: Re-render slides for a carousel with missing slides
      Given a completed carousel with hero images but missing PT/EN slides
      When I POST to "/api/admin/carousels/render-slides"
      Then the response status should be 200
      And the response should contain total >= 1
      And the response should contain updated >= 1
      And the response should contain failed = 0

  Scenario: Report failure when Playwright export errors
      Given a completed carousel whose slide export raises an error
      When I POST to "/api/admin/carousels/render-slides"
      Then the response status should be 200
      And the response should contain failed >= 1
      And the response should include an error message for that carousel

  Scenario: Skip carousels that already have all slides
      Given a completed carousel with all PT and EN slides on disk
      When I POST to "/api/admin/carousels/render-slides"
      Then the response status should be 200
      And the updated count should be 0 for that carousel

  Scenario: Skip carousels that are not completed
      Given a carousel in "designing" status
      When I POST to "/api/admin/carousels/render-slides"
      Then the carousel should not be included in processing

  Scenario: Return 403 for non-admin user
      Given I am authenticated as an editor
      When I POST to "/api/admin/carousels/render-slides"
      Then the response status should be 403

  Scenario: Return 401 for unauthenticated user
      Given I am not authenticated
      When I POST to "/api/admin/carousels/render-slides"
      Then the response status should be 401
