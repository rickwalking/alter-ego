Feature: Every page has its own localized title
  As a visitor or the owner with several tabs, bookmarks and history entries
  I want each page's <title> to name the page
  So that tabs are distinguishable and screen readers announce where I am (WCAG 2.4.2)

  Scenario: Public pages have their own titles
    When I open "/blog", "/login", "/403" or an unknown URL
    Then the title reads "Blog · Pedro Marins", "Sign in · Pedro Marins", "Access denied · Pedro Marins" or "Page not found · Pedro Marins"

  Scenario: Dashboard pages have their own titles
    When I open a dashboard page such as the calendar, rubrics, palettes or the user admin
    Then the title names that page, e.g. "Calendar · Pedro Marins"

  Scenario: Titles follow the interface language
    Given the interface language is Portuguese
    When I open the calendar
    Then the title reads "Calendário · Pedro Marins"

  Scenario: Page Open Graph tags keep a type and the page description
    When a page sets its own title
    Then its Open Graph tags still carry og:type "website"
    And "/blog" also carries its own description as description and og:description

  Scenario: A page without its own description keeps the site og:description
    When I open "/login", "/403", an unknown URL or the dashboard
    Then its Open Graph tags carry og:type "website" and the site description as og:description
