Feature: Presentation persistence single-writer / ACL (AE-0118)
  As the presentation bounded context
  I want a single writer/ACL over the presentation carousel columns + slide rows
  So that presentation writes are owned in one place and the
  artifact_version <-> lock_version compound CAS is preserved exactly while
  sharing the lock_version token with the editorial resume CAS without clobbering.

  Background:
    Given a persisted carousel project row

  Scenario: the ACL maps a legacy row to the presentation VIEW
    When the ACL loads the presentation view for the project
    Then the view exposes the presentation project and the verbatim lock_version

  Scenario: design-token refresh persists through the single write owner
    When the owner refreshes the project design_tokens and commits
    Then the persisted row has the new design_tokens and only the owner committed

  Scenario: PDF-path / presentation-column writes persist through the owner
    When the owner updates the project presentation columns and commits
    Then the persisted row reflects the presentation columns

  Scenario: slide rows are created and updated through the owner
    When the owner creates a slide and then updates it and commits
    Then the persisted slide reflects the create then the update

  Scenario: the activation CAS preserves the artifact_version<->lock_version pairing
    When the owner activates an artifact against the current lock_version
    Then artifact_version and lock_version are bumped together by exactly one

  Scenario: a stale activation source_lock_version is rejected (no silent overwrite)
    Given the lock_version has advanced past the activation source
    When the owner activates an artifact against the stale source
    Then the activation is rejected with an artifact-build conflict

  Scenario Outline: a presentation activation and an editorial resume bump do not clobber
    Given two writers race the shared lock_version from the same source version
    When one runs the activation CAS and the other runs the resume CAS as <order>
    Then exactly one succeeds, the other gets its conflict, and lock_version
      advances by exactly one

    Examples:
      | order                     |
      | activation_then_resume    |
      | resume_then_activation    |
