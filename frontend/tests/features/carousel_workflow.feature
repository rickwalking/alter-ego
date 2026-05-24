Feature: Carousel Creation with Enhanced Workflow
  As a content creator
  I want to guide the AI through each phase of carousel creation
  So that the output matches my vision and maintains quality

  Background:
    Given I am logged in as "Pedro"
    And I have a persona profile "Pedro's Professional Voice"
    And I have a quality rubric "Instagram Carousel Standard"

  # === HAPPY PATH ===

  Scenario: Create carousel with full workflow
    Given I navigate to the carousel creation page
    When I fill in the creative brief:
      | field        | value                                      |
      | topic        | "AI Security Threats in 2026"              |
      | audience     | "CISOs and security architects"              |
      | instructions | "Focus on real breaches, not predictions"   |
    And I upload source materials:
      | type     | title                    |
      | document | "Q1 2026 Breach Report"  |
      | url      | "https://example.com/..."|
    And I select persona "Pedro's Professional Voice"
    And I select rubric "Instagram Carousel Standard"
    And I submit the brief
    Then the project status should be "researching"
    And I should see "Research in progress..."

    When the research phase completes
    Then I should see research findings with key points
    And I should see a "Review Research" button

    When I click "Review Research"
    And I add a note: "Add more details about the Marriott breach"
    And I click "Approve & Continue"
    Then the project status should be "outlining"
    And I should see "Outline in progress..."

    When the outline phase completes
    Then I should see a slide-by-slide outline
    And I should be able to reorder slides
    And I should be able to edit slide titles

    When I move slide 3 to position 1
    And I edit slide 2 title to "The Real Cost of AI Breaches"
    And I click "Approve Outline"
    Then the project status should be "content_drafting"
    And I should see "Drafting slide content..."

    When the content phase completes
    Then I should see draft text for each slide
    And each slide should show:
      | field            | value                          |
      | draft text       | "AI breaches cost $4.2M on avg..." |
      | sources used     | "Q1 2026 Breach Report"        |
      | confidence score | "0.92"                         |

    When I edit slide 1 text to add a personal anecdote
    And I click "Approve Content"
    Then the project status should be "designing"

    When the design phase completes
    Then I should see the styled carousel preview
    And I should see a "Request Design Changes" button

    When I click "Approve Design"
    Then the project status should be "image_generating"

    When the images phase completes
    Then I should see generated images for each slide
    And I should see an "Upload Custom Image" button

    When I replace image 2 with a custom upload
    And I click "Approve Images"
    Then the project status should be "final_review"
    And I should see a quality score of "87/100"
    And I should see "All criteria passed"

    When I click "Publish"
    Then the project status should be "published"
    And I should see "Carousel published successfully"
    And the carousel should be visible on the public page

  # === EDGE CASES ===

  Scenario: Reject research and provide feedback
    Given the research phase has completed
    When I review the findings
    And I click "Request Changes"
    And I enter feedback: "Include more recent sources from 2026"
    Then the project should return to "researching" phase
    And the AI should re-research with the new criteria
    And I should see "Re-researching with updated criteria..."

  Scenario: Skip phases for trusted user
    Given I have "trusted_user" role
    And I have created 10+ carousels with 90%+ approval rate
    When I create a new carousel
    And I enable "Skip to Content Draft" option
    Then the project should skip "research" and "outline" phases
    And start directly at "content_drafting"

  Scenario: Content fails quality rubric
    Given the content phase has completed
    When the quality agent scores the content:
      | criterion         | score | threshold |
      | E-E-A-T           | 45    | 70        |
      | originality       | 60    | 75        |
      | voice_consistency | 80    | 70        |
    Then I should see "Quality check failed"
    And I should see specific feedback:
      | criterion   | issue                          |
      | E-E-A-T     | "Lacks first-hand experience"  |
      | originality | "Too similar to source material"|
    And the project should remain in "content_drafting" phase
    And I should see "AI is revising based on feedback..."

  Scenario: Workflow interruption and recovery
    Given the project is in "content_drafting" phase
    When the server restarts
    And I navigate back to the project
    Then the project should resume from "content_drafting" phase
    And I should see "Resuming from checkpoint..."
    And no progress should be lost

  Scenario: Concurrent editing prevention
    Given the project is in "content_review" phase
    And "Pedro" is reviewing the content
    When "Maria" attempts to approve the phase
    Then "Maria" should see "This phase is being reviewed by Pedro"
    And the approval should be rejected
    And "Maria" should see a "Request Review Handoff" option

  Scenario: Source material limits
    Given I am creating a carousel
    When I attempt to upload a 500MB video file as source material
    Then I should see "Source material must be under 50MB"
    And the upload should be rejected
    And I should see "Consider compressing or providing a transcript"

  # === ERROR CASES ===

  Scenario: AI generation timeout
    Given the project is in "image_generating" phase
    When the image generation exceeds 5 minutes
    Then I should see "Image generation is taking longer than expected"
    And I should see a "Retry" button
    And I should see a "Skip Images & Use Placeholders" option
    And the project should remain in "image_generating" phase

  Scenario: Invalid persona configuration
    Given I select a persona with no writing samples
    When I submit the brief
    Then I should see "Persona has no writing samples. Add examples first."
    And the brief submission should be blocked
    And I should see a link to "Edit Persona"
