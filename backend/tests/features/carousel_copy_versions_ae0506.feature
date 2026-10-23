Feature: Every saved caption and LinkedIn post edit is kept as a version
  As the owner of a carousel
  I want each saved edit of the caption and the LinkedIn posts kept with who made it and when
  So that I can see how a text changed and bring back an earlier one

  Background:
    Given a carousel owned by an editor, with a generated caption and LinkedIn posts

  Scenario: Saving a changed caption stores the original and the new text as versions
    When the owner saves a new caption
    Then the versions list holds the generated caption as version 1 with no author
    And the new caption as version 2 by the owner, with its time

  Scenario: A later edit of the same text stores only the new text
    Given the owner already saved one caption edit
    When the owner saves another caption
    Then one more version is stored, with the next number

  Scenario: One save of several texts stores a version of each
    When the owner saves a new caption and a new Portuguese LinkedIn post in one save
    Then the versions are, in order, the generated caption, the new caption, the generated post and the new post

  Scenario: A text changed outside the editor is kept before the next edit
    Given the owner saved one caption edit
    And the chat refine then rewrote the caption
    When the owner saves another caption
    Then the refined caption is stored as a previous text before the new caption
    And it can be restored

  Scenario: The history is read a page at a time
    Given a carousel with more versions than one page
    When the owner asks for the versions with a limit
    Then the newest versions up to the limit come back with the cursor of the next page
    And the next page holds the older versions and no cursor

  Scenario: A text that did not change stores no version
    When the owner saves the caption with the text it already has
    Then no version is stored

  Scenario: Each carousel numbers its versions from 1
    Given two carousels of the owner
    When the owner saves a caption on each
    Then each carousel's versions start at 1

  Scenario: Only the owner or an admin sees the versions
    When another editor asks for the versions
    Then the request is refused with 403
    And an admin gets the versions

  Scenario: Only the owner or an admin restores a version
    When another editor restores a version
    Then the request is refused with 403
    And an admin can restore it

  Scenario: Restoring a version saves its text as a new version
    Given the owner saved a caption edit
    When the owner restores version 1 with the current lock version
    Then the caption is the generated caption again
    And a new version records the restore of version 1
    And the response carries the next lock version

  Scenario: Restoring the current text changes nothing
    When the owner restores a version whose text is the current text
    Then the response carries the current text and the sent lock version
    And no version is stored and the lock version does not move

  Scenario: A restore is refused when it cannot be applied
    When the owner restores a version with a stale lock version
    Then the request is refused with 409 "version_conflict"
    When the owner restores a version that does not exist
    Then the request is refused with 404
    When the carousel's caption is already published on Instagram
    Then restoring a caption version is refused with 409 "caption_published"
    When a workflow run is active
    Then the restore is refused with 409 "resume_already_in_progress"
    When the restore has no If-Match
    Then the request is refused with 428
    When the carousel or the version's field is unknown
    Then the request is refused with 404

  Scenario: The deploy fixes the content versions unique index once
    Given a Postgres database whose content_versions unique index is global
    When the one-shot runs with --apply --verify
    Then the global index is dropped and the per-content unique index exists
    And running it again changes nothing
    And --verify fails while the global index is present
    And a database without the content_versions table is left alone and passes --verify
