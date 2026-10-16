Feature: A resumed workflow keeps the project's persona (AE-0397)
  The resume runner passed no persona, so a content phase reached through a
  resume (every autopilot gate approval) never scored the voice and every POV
  autopilot run escalated with persona_not_scored.

  Scenario: A resume voices the content with the project's persona
    Given a project created with the persona "Pedro"
    When its workflow is resumed
    Then the resumed phase receives the persona "Pedro"

  Scenario: The project's persona is loaded for the resume
    Given a project bound to a persona
    When the resume loads its persona
    Then that persona is returned

  Scenario: A project without a persona resumes without one
    Given a project with no persona, or no project row
    When the resume loads its persona
    Then no persona is used

  Scenario: A persona id that no longer exists resumes without one
    Given a project whose persona was deleted
    When the resume loads its persona
    Then no persona is used
