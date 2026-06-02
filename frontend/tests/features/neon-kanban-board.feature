Feature: NeonKanbanBoard Component
  As a developer using the NeonKanbanBoard organism
  I want to render workflow columns with cards
  So that pipeline status is visible on the dashboard

  Scenario: Kanban renders column status labels
    When I render a NeonKanbanBoard with a Research column
    Then I should see column title "Research"

  Scenario: Kanban renders card titles
    When I render a NeonKanbanBoard with one card titled "DeepSeek V4"
    Then I should see card title "DeepSeek V4"
