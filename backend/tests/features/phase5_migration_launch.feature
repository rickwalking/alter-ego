Feature: Phase 5 migration and launch
  As a platform operator
  I want to migrate legacy data and deploy with feature flags
  So that the editorial workflow launches safely

  Background:
    Given the Phase 5 migration service is available
    And feature flags control rollout of new endpoints

  Scenario: MIG-001 Migrate creative brief from legacy fields
    Given a carousel project with topic "AI agents" and no creative_brief
    When the Phase 5 migration runs
    Then creative_brief contains the topic and audience fields

  Scenario: MIG-002 Create default persona from carousel outputs
    Given completed carousel projects with captions and blog content
    When the Phase 5 migration runs
    Then a default persona is created with writing samples

  Scenario: MIG-003 Create default quality rubric
    Given no default quality rubric exists
    When the Phase 5 migration runs
    Then a default rubric is created with editorial criteria

  Scenario: MIG-004 Backfill workflow state for in-progress projects
    Given a carousel project with status "researching"
    When the Phase 5 migration runs
    Then current_phase is "research" and phase_status is "in_progress"

  Scenario: DEPLOY-003 Feature flag disables quality endpoints
    Given feature_flag_quality_checks is disabled
    When an editor requests SEO analysis
    Then the response status is 503

  Scenario: MON-002 Workflow failure alerts
    Given a carousel project failed in the last hour
    When the workflow alert worker runs
    Then a workflow failure alert is emitted for admins
