Feature: The owner sees and restores versions of the caption and the LinkedIn posts
  As the owner of a carousel
  I want the history of each text under its editor
  So that I can see who changed it and bring back an earlier version

  Background:
    Given a carousel whose caption was generated and then edited by the owner

  Scenario: The history lists the versions of the text under its editor
    When the owner opens the caption editor on the publish page or in Revisão final
    Then "Histórico" lists the caption versions, newest first
    And each shows its number, who wrote it (or "Texto gerado"), when, and the text

  Scenario: The LinkedIn history shows the versions of both languages
    When the owner opens the LinkedIn editor
    Then the history lists the PT and EN post versions, each with its language

  Scenario: Restoring a version sends it with the current lock version
    When the owner clicks "Restaurar" on version 1
    Then POST /api/carousels/{id}/copy/versions/1/restore is sent with If-Match the current lock version
    And the texts, the history and the lock version are refetched
    And the restore stays "Restaurando…" until that refetch is done

  Scenario: Approve and send back wait while a restore runs
    Given the reviewer clicked "Restaurar" in Revisão final
    Then "Aprovar" and "Pedir mudanças" stay disabled until the restore and its refetch are done

  Scenario: A text with unsaved edits cannot be restored
    Given the owner edited the caption without saving
    Then "Restaurar" is disabled with a hint to save or discard the edit first

  Scenario: A refused restore explains why
    When the restore is refused as stale or as an already published caption
    Then the history shows the matching message
