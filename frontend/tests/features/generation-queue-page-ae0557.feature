Feature: Generation queue page
  The generation queue lives on its own admin page, the board keeps a compact
  summary, and queue rows link to their carousels.

  Background:
    Given an admin signed in to the dashboard

  Scenario: The queue has its own page
    When the admin opens the queue page
    Then the queue title, subtitle and sections are shown
    And every queue action is available including Processar fila agora
    And a link leads back to the workflow board

  Scenario: The Fila nav item is admin-only
    Given an admin on the dashboard sidebar
    Then Fila appears right after Workflow Board
    Given an editor on the dashboard sidebar
    Then Fila does not appear

  Scenario: The board keeps only a queue summary
    When the workflow board renders
    Then the full queue panel is gone
    And a compact summary links to the queue page
    And an empty queue reads Fila vazia

  Scenario: Queue rows link to their carousels
    Given a queue row whose run has a carousel
    When the row renders
    Then the theme title links to the carousel detail page
    Given a backlog theme without a carousel
    When the row renders
    Then the title stays plain text
