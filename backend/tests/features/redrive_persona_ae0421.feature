Feature: A re-driven phase drafts and scores with the project persona (AE-0421)

  On 2026-10-18 two pov_news carousels had content re-driven after an LLM outage. The re-drive
  ran the content node without the persona, so the drafts lost the voice and were never scored
  (autopilot escalation persona_not_scored).

  Scenario: The re-drive loads the project's persona
    Given a parked carousel whose next node is content
    When the autopilot re-drives the parked node
    Then the project's persona is loaded, as for a resume

  Scenario: The re-run node receives the persona
    Given the project's persona
    When the parked node is re-driven
    Then the workflow input of the re-run carries that persona

  Scenario: A project without a persona still re-drives
    Given a carousel with no persona
    When the parked node is re-driven
    Then the node runs with no persona, as before
