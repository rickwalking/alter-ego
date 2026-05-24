# Phase 3: Workflow & Collaboration

Feature: Event-driven workflow engine
  As a content platform
  I want workflow events persisted and published
  So that audit trails and notifications stay in sync

  Scenario: Emit phase change event
    Given a carousel project exists
    When the workflow phase changes to "research"
    Then an audit log entry should be created
    And the event should be published to the content events stream

Feature: In-app notifications
  As a reviewer
  I want to receive review request notifications
  So that I know when content awaits my approval

  Scenario: Assign reviewer to blog post
    Given a blog post in draft status
    When an editor assigns a reviewer
    Then the reviewer should receive an in-app notification
    And an email notification should be logged

Feature: Optimistic locking
  As an editor
  I want concurrent edits detected
  So that my work is not silently overwritten

  Scenario: Version conflict on blog post update
    Given a blog post with lock_version 2
    When a client sends If-Match 1
    Then the update should be rejected with version_conflict

Feature: Scheduled publishing
  As a content creator
  I want to schedule approved posts
  So that they publish automatically at the chosen time

  Scenario: Schedule approved blog post
    Given an approved blog post
    When I schedule it for a future datetime
    Then scheduled_publish_at should be set
    And a calendar entry should appear

Feature: Content calendar
  As an editor
  I want a calendar view of content
  So that I can plan publishing

  Scenario: View calendar entries
    Given scheduled and published blog posts exist
    When I open the content calendar
    Then I should see entries grouped by date

Feature: Workflow Kanban board
  As a content creator
  I want to see projects by workflow phase
  So that I can track editorial progress

  Scenario: View Kanban columns
    Given carousel projects in different phases
    When I open the workflow board
    Then I should see columns for each editorial phase
