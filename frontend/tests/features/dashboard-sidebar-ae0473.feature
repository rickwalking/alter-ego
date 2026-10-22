Feature: The dashboard sidebar reaches every dashboard page and shows no fake counts
  As the site owner
  I want every dashboard page in the sidebar and no invented unread badge
  So that I can reach Palettes, Knowledge, Analytics and Users and trust what the sidebar tells me

  Scenario: The sidebar links Palettes, Knowledge and Analytics
    Given I am signed in as an editor or an admin
    When the dashboard sidebar is shown
    Then it links "/dashboard/palettes", "/dashboard/knowledge" and "/dashboard/analytics"

  Scenario: Only admins see the user administration link
    Given I am signed in as an admin
    Then the sidebar links "/admin/users"
    But an editor's sidebar does not

  Scenario: Chat shows no invented unread badge
    When the dashboard sidebar is shown
    Then the Chat link shows no badge

  Scenario: Every sidebar label exists in both languages
    Then each sidebar section and item label has an English and a Portuguese message
