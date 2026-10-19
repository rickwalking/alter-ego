# RECONCILED IN PLACE (AE-0424). The prior version promised a rich-text editor
# and an asset library, which remain out of scope. The review workflow
# (submit → review → approve) and scheduled publish ARE in scope (owner revision)
# and are backed by the existing blog_post_workflow routes. The editor is now a
# section editor over blog.v2 with per-section/cover image controls, a
# persona-voice rewrite, version history on save, an unsaved-changes guard,
# PT/EN content buttons and review/schedule/publish. Version history + AI suggest
# are kept (and corrected): history is written on every save, and ai-suggest
# returns plain text, never a fenced JSON envelope.

Feature: Blog Post Creation with the section editor (reconciled)
  As the owner
  I want to write a blog post as sections with my own voice and generated images
  So that I publish content that sounds like me and looks editorial

  Background:
    Given I am logged in as "Pedro"
    And I have a persona profile "Pedro's Professional Voice"
    And the post is a blog.v2 document under edit

  # === HAPPY PATH ===

  Scenario: Create a draft and edit it as sections
    Given I navigate to the blog post creation page
    When I enter the title "The Real Cost of AI Security Breaches"
    And I click "Create Draft"
    Then the post status should be "draft"
    And I should see one section card for each stored section
    And I should not see a single rich-text textarea for the whole body

  Scenario: AI suggest returns plain text (no fenced JSON)
    Given I am editing section "intro"
    When I type "AI security breaches are becoming more frequent..."
    And I click "AI Suggest"
    Then I should see plain-text suggestions, never a ```json envelope
    And a nested envelope suggestion is shown unwrapped as plain text

  Scenario: Insert a suggestion into one section
    Given AI suggestions are shown for section "intro"
    When I accept the "add_opinion" suggestion
    Then the suggestion is inserted into that section's body
    And no other section changes

  Scenario: Manage a section's image
    Given a section "intro" with no image
    When I click "Generate Image" for that section
    Then I should see a preview of the generated image
    When I click "Use This Image"
    Then the section gets that image with a non-empty alt (defaulting to the heading)
    And I can edit its alt text and caption

  Scenario: Manage the cover
    Given a post with no cover
    When I generate the cover and save
    Then the post's featured image equals the cover url

  Scenario: Rewrite one section in my voice
    Given a section "intro" with a generic body
    When I click "Rewrite this section in my voice"
    Then only that section's body is replaced
    And I can see the voice score for the post

  Scenario: Plain publish from the editor
    Given a draft with at least one non-empty section
    When I click "Publish"
    Then the post status should be "published"
    And the post should be visible at /blog/{id}

  # === EDGE CASES ===

  Scenario: Version history and rollback
    Given I have a blog post edited and saved twice
    When I open "Version History"
    Then I should see one entry per save, newest first

    When I select the first version
    And click "Restore This Version"
    Then a new version should be created from it
    And the editor content should match that version

  Scenario: Unsaved changes are guarded
    Given I have edited a section without saving
    When I navigate away or close the tab
    Then a leave-confirmation should be shown
    And my edit should not be silently lost

  Scenario: Concurrent save conflict
    Given the post is at lock version 2
    And another tab saved first
    When I save with a stale version
    Then I should see a conflict message
    And my unsaved text should be preserved in the editor

  Scenario: Unpublish and re-publish
    Given a blog post is "published"
    When I click "Unpublish"
    Then the post status should be "draft"
    And the public URL should return 404

    When I edit the post and click "Publish"
    Then the post should be visible again at the same URL

  # === ERROR CASES ===

  Scenario: AI suggestion on empty selection
    Given I am editing a blog post
    When I click "AI Improve" without selecting any text
    Then I should see "Please select text to improve"
    And no AI request should be made

  Scenario: Image generation failure offers a retry
    Given I request an AI-generated image for a section
    When the image generation fails
    Then I should see "Image generation failed"
    And a retry control should be available on that slot
    And the rest of the document should remain editable

  Scenario: Publishing an empty document is blocked
    Given every section's body is empty
    When I click "Publish"
    Then I should see a validation message
    And the post should stay "draft"

  Scenario: Submit, approve and schedule
    Given a draft with at least one non-empty section
    When I submit it for review and the reviewer approves it
    Then the post status should be "approved"
    When I schedule a future publication date
    Then the post should publish at that time
