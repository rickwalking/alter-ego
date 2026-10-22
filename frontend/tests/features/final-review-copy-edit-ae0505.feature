Feature: The reviewer edits the caption and the LinkedIn posts in the final review step
  As the owner reviewing a carousel in "Revisão final"
  I want to fix the Instagram caption and the LinkedIn posts where I review them
  So that the publish page shows, copies and publishes the text I approved

  Background:
    Given a carousel at the final review step at lock version 5
    And the saved project has a caption and PT and EN LinkedIn posts

  Scenario: The reviewer saves an edited caption in the final review
    When the reviewer opens "Legenda", edits the caption and clicks Save
    Then the caption is sent to PATCH /api/carousels/{id}/copy with If-Match 5
    And the tab shows "Salvo"

  Scenario: The reviewer saves a LinkedIn post per language
    When the reviewer opens "LinkedIn", picks EN, edits the post and clicks Save
    Then only linkedin_post_en is sent

  Scenario: The final review shows the saved project text
    Given the workflow checkpoint still holds the generated caption
    And the project holds the caption saved on the publish page
    When the reviewer opens "Legenda"
    Then the editor shows the saved project caption

  Scenario: The checkpoint text is shown when the project has none
    Given the project has no caption yet
    When the reviewer opens "Legenda"
    Then the editor shows the caption of the workflow checkpoint

  Scenario: A save refreshes the workflow state and the project
    When the reviewer saves the caption
    Then the workflow state and the project are refetched

  Scenario: A stale save explains itself and refetches
    Given the carousel changed after the review was loaded
    When the save is refused as "version_conflict"
    Then the tab shows the stale message and keeps the edited text
    And the workflow state and the project are refetched

  Scenario: Switching tabs keeps unsaved drafts
    Given the reviewer edited the caption without saving
    When they open "LinkedIn" and come back to "Legenda"
    Then the edited caption is still in the editor

  Scenario: Leaving the review with unsaved edits asks first
    Given the reviewer edited a text without saving
    When they follow a link to another dashboard page
    Then the page's own dialog asks whether to discard the edits
    And with nothing unsaved the link is followed at once

  Scenario: The blog body is edited in the blog editor
    When the reviewer opens "Blog"
    Then the blog preview is shown with "Abrir no editor do blog"
    When they click it and the carousel already has a blog post
    Then the blog editor of that post opens
