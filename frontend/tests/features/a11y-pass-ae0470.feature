Feature: Public and admin pages pass the basic accessibility checks
  As a keyboard or screen-reader user, or someone reading on a dim screen
  I want readable text, honest link names, one announced heading and labelled fields
  So that I can use marinssolutions.com and the admin without guessing

  Scenario: Keyboard users can skip to the main content
    Given I am on a page with the public header, the dashboard sidebar, the admin sidebar or the login header
    When I press Tab once
    Then the first focus is a "Skip to content" link that moves to the page's main content

  Scenario: Dim text meets WCAG AA contrast
    Given the shared dim text colour on the page, card and sidebar backgrounds
    Then its contrast ratio is at least 4.5:1

  Scenario: Links are named by their visible text
    Given the header logo link and the homepage capability cards
    Then each link's accessible name contains the text it shows

  Scenario: The homepage heading is announced once
    Given the homepage hero heading with its glitch effect
    Then a screen reader hears "Chat with my Alter-Ego" once

  Scenario: Decorative placeholder text stays out of link names
    Given a latest-post card whose image placeholder reads "carousel_preview.jpg"
    Then the placeholder is hidden from assistive technology

  Scenario: Admin user form fields have labels
    Given the create-user and edit-user dialogs
    Then every field is reachable by its visible label

  Scenario: Admin buttons and errors meet contrast
    Given the admin primary buttons and error banners
    Then they use the darker primary and red shades that meet 4.5:1

  Scenario: Dashboard headings keep their order
    Given the dashboard overview
    Then the quick-action titles are level-3 headings under the level-2 section heading
