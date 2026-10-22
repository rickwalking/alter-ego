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
