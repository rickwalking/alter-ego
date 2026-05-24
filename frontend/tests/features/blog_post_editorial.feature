Feature: Blog Post Creation with Editorial Workflow
  As a content creator
  I want to write blog posts with AI assistance and editorial review
  So that I publish high-quality, original content

  Background:
    Given I am logged in as "Pedro"
    And I have a persona profile "Pedro's Professional Voice"

  # === HAPPY PATH ===

  Scenario: Create and publish blog post with AI assistance
    Given I navigate to the blog post creation page
    When I enter the title "The Real Cost of AI Security Breaches"
    And I select template "Opinion Piece"
    And I click "Create Draft"
    Then the post status should be "draft"
    And I should see a rich text editor

    When I type "AI security breaches are becoming more frequent..."
    And I click "AI Suggest"
    Then I should see suggestions:
      | type        | suggestion                                           |
      | improve     | "Add a specific statistic about 2026 breach costs" |
      | shorten     | "This paragraph is 200 words — consider splitting"   |
      | add_opinion | "Pedro's take: I predicted this in my 2024 talk..."  |

    When I click the "add_opinion" suggestion
    Then the text should be inserted with Pedro's opinion
    And I should see "Added based on your persona"

    When I upload an image "breach-chart.jpg"
    And I position it after paragraph 2
    Then the image should appear in the editor
    And I should see "Alt text: AI security breach cost chart showing..."

    When I add a source reference:
      | type  | title                    | url                        |
      | url   | "2026 Breach Report"     | "https://example.com/..."  |
    Then the source should appear in the references section
    And in-text citations should be updated

    When I click "Submit for Review"
    Then the post status should be "under_review"
    And "Pedro" should receive a review notification

    When "Pedro" reviews the post
    And adds a comment on paragraph 3: "Add more detail about the Marriott case"
    And clicks "Request Changes"
    Then the post status should be "draft"
    And I should see the comment in the editor

    When I address the comment by adding Marriott details
    And click "Resolve Comment"
    And click "Submit for Review" again
    Then the post status should be "under_review"

    When "Pedro" approves the post
    Then the post status should be "approved"
    And I should see "Ready to publish"

    When I click "Publish Now"
    Then the post status should be "published"
    And the post should be visible at "/blog/the-real-cost-of-ai-security-breaches"
    And the post should appear in the RSS feed
    And a social media preview should be generated

  Scenario: AI generates image for blog post
    Given I am editing a blog post in "draft" status
    When I click "Generate Image"
    And I enter prompt: "Abstract visualization of AI security vulnerabilities"
    Then the AI should generate an image
    And I should see a preview of the generated image
    And I should see "Generated in 12 seconds"

    When I click "Use This Image"
    Then the image should be inserted into the post
    And the alt text should be auto-generated
    And the image should be stored in the asset library

  # === EDGE CASES ===

  Scenario: Version history and rollback
    Given I have a published blog post
    And it has 5 versions in history
    When I navigate to "Version History"
    Then I should see a list of versions with:
      | version | date       | author | change_summary              |
      | 5       | 2026-05-20 | Pedro  | "Added conclusion paragraph"|
      | 4       | 2026-05-19 | Pedro  | "Fixed typo in title"       |

    When I select version 4
    And click "Preview Version"
    Then I should see the post as it appeared in version 4

    When I click "Restore This Version"
    And confirm "This will create version 6 with the content from version 4"
    Then a new version 6 should be created
    And the post content should match version 4
    And the post status should remain "published"
    And the public URL should serve the updated content

  Scenario: Collaborative editing with conflict
    Given "Pedro" is editing paragraph 3 of a blog post
    And "Maria" is editing the same paragraph simultaneously
    When "Pedro" saves changes
    And "Maria" attempts to save changes 2 seconds later
    Then "Maria" should see "This section was modified by Pedro"
    And she should see a diff view showing both versions
    And she should be able to:
      | option                    | action                                  |
      | Keep my changes           | Overwrite with Maria's version          |
      | Keep Pedro's changes      | Discard Maria's changes                 |
      | Merge both                | Combine changes (if non-conflicting)    |
      | Save as new version       | Create a branch for review              |

  Scenario: Scheduled publishing
    Given a blog post is in "approved" status
    When I set scheduled publish to "2026-06-01 09:00:00"
    And click "Schedule"
    Then the post status should be "approved"
    And I should see "Scheduled for June 1, 2026 at 9:00 AM"
    And the post should not be publicly visible

    When the scheduled time arrives
    Then the post should automatically change status to "published"
    And I should receive a notification "Your post is now live"

  Scenario: Unpublish and edit
    Given a blog post is "published"
    When I click "Unpublish"
    And confirm "This will make the post invisible to readers"
    Then the post status should be "draft"
    And the public URL should return 404
    And SEO crawlers should see "noindex"

    When I edit the post and add new content
    And click "Publish"
    Then the post should be visible again
    And the URL should remain the same
    And returning readers should see the updated content

  # === ERROR CASES ===

  Scenario: AI suggestion on empty selection
    Given I am editing a blog post
    When I click "AI Improve" without selecting any text
    Then I should see "Please select text to improve"
    And no AI request should be made

  Scenario: Duplicate slug prevention
    Given a blog post exists with slug "ai-security-2026"
    When I create a new post with title "AI Security 2026"
    Then the slug should be auto-generated as "ai-security-2026-2"
    And I should see "Slug adjusted to avoid conflict"

  Scenario: Image generation failure
    Given I request an AI-generated image
    When the image generation fails after 3 retries
    Then I should see "Image generation failed"
    And I should see fallback options:
      | option                  | description                          |
      | Retry                   | Try again with same prompt           |
      | Simplify Prompt         | Use a shorter, simpler prompt        |
      | Upload Image            | Use your own image instead           |
      | Skip Image              | Continue without an image            |
