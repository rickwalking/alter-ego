Feature: The workflow CAS version survives live updates (AE-0447)
  The publish step's cover picker always answered 409 "O carrossel mudou" on prod
  (carousel 787085ba, 2026-10-21): the SSE merge rebuilt the workflow state without
  `lock_version`, so the page sent the fallback version 1 while the server was at 10.

  Scenario: A live-stream update never drops the CAS lock version
    Given the workflow state has lock_version 10
    When a progress event or a full snapshot without lock_version is merged
    Then the merged state still has lock_version 10
    And a snapshot that carries lock_version 11 replaces it

  Scenario: The pick sends the server's current version, not page state
    Given the server's workflow state is at lock_version 11
    When the owner picks another cover photo
    Then the picker reads the workflow state right before the switch
    And it sends expected_version 11
