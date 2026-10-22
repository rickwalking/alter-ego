Feature: The owner saves the Instagram caption and the LinkedIn posts of a carousel
  As the owner of a carousel
  I want my edits to the caption and the LinkedIn posts saved on the server
  So that a reload, a copy or an Instagram publish uses the text I wrote

  Background:
    Given a completed carousel owned by an editor, with a generated caption and LinkedIn posts

  Scenario: The owner saves an edited caption
    When the owner sends the new caption with the current lock version
    Then the response carries the saved caption and the next lock version
    And reading the carousel again returns the new caption

  Scenario: The LinkedIn posts are saved per language
    When the owner sends new Portuguese and English LinkedIn posts
    Then reading the carousel again returns both posts
    And the caption is unchanged

  Scenario: Someone else cannot change the texts
    When another editor who does not own the carousel sends a new caption
    Then the request is refused with 403
    And the caption is unchanged

  Scenario: An admin can save the texts of any carousel
    When an admin sends a new LinkedIn post for the carousel
    Then the post is saved

  Scenario: A save without the lock version is refused
    When the owner sends a new caption without If-Match
    Then the request is refused with 428

  Scenario: A save from a stale page is refused
    Given the carousel changed after the page was loaded
    When the owner sends a new caption with the old lock version
    Then the request is refused with 409 "version_conflict"
    And the caption is unchanged

  Scenario: The caption of a carousel published on Instagram is read-only
    Given the carousel was published on Instagram
    When the owner sends a new caption
    Then the request is refused with 409 "caption_published"

  Scenario: The texts cannot change while a workflow run is active
    Given a workflow run is in progress for the carousel
    When the owner sends a new caption
    Then the request is refused with 409 "resume_already_in_progress"

  Scenario: An empty or oversized save is rejected
    When the owner sends no text, or a caption longer than 2200 characters
    Then the request is refused with 422

  Scenario: Saving the texts keeps the carousel approved for publish
    Given the carousel is approved for publish
    When the owner saves a new caption
    Then the carousel is still approved for publish
    And publishing it on Instagram is not refused and sends the new caption

  Scenario: Instagram publishing sends the saved caption
    Given the carousel has a saved caption
    When the owner publishes it on Instagram without sending a caption
    Then the saved caption is the one published

  Scenario: A caption the page has not saved is never published
    Given the carousel has a saved caption
    When a publish request carries a different caption
    Then the request is refused with 409 "caption_not_saved"
    And nothing is published

  Scenario: A carousel without a saved caption is not published
    Given the carousel has no saved caption
    When the owner publishes it on Instagram
    Then the request is refused with 409 "caption_missing"
    And nothing is published
