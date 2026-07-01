# Carousel Editorial Publish Fixes
# Traceability: docs/plans/carousel-editorial-publish-fixes.md

Feature: Seven-slide editorial outline contract
  As an editor
  I want carousels capped at seven slides
  So that output matches the legacy pipeline structure

  Scenario: Outline normalization trims excess slides
    Given an outline with 10 slides
    When the outline is normalized for editorial workflow
    Then the outline should contain exactly 7 slides
    And slide 1 should have type "intro"
    And slide 7 should have type "cta"

Feature: Editorial distribution pack
  As an editor
  I want captions and bilingual blog copy after content
  So that the publish workspace is ready for distribution

  Scenario: Blog markdown separates PT and EN when translations exist
    Given slide drafts with Portuguese body text
    And English translations for each slide
    When the distribution pack builds blog translations
    Then blog_pt should differ from blog_en when EN text is provided

Feature: Workflow board published column
  As an editor
  I want published carousels on the Kanban board
  So that I can find completed work

  Scenario: Kanban columns include published phase
    Given the workflow board API columns list
    Then the last column phase should be "published"

Feature: GLM flat draft blob normalization
  As the carousel content pipeline
  I want flat or locale-suffixed slide draft blobs normalized into presentations
  So that GLM-generated slides render body copy instead of title-only slides

  Scenario: Locale-suffixed intro blob maps subtitle_pt into the body
    Given a slide draft whose draft_text is a flat blob with heading_pt and subtitle_pt
    When the slide draft is normalized
    Then the Portuguese presentation body equals the subtitle_pt text
    And the presentation body is not the raw blob string

  Scenario: Clean single-locale blob maps body into the presentation
    Given a slide draft whose draft_text is a flat blob with plain heading and body
    When the slide draft is normalized
    Then the Portuguese presentation body equals the body text

  Scenario: Summary points with title_pt items localize per locale
    Given a summary slide draft whose points items use title_pt and body_pt keys
    When the slide draft is normalized
    Then each Portuguese summary point has a non-empty title

  Scenario: Non-dict draft_text is left untouched
    Given a slide draft whose draft_text is plain prose
    When the slide draft is normalized
    Then the slide draft is returned unchanged

Feature: Final-review send-back preserves the target phase (AE-0290)
  As an editor sending an approved carousel back to content
  I want the checkpoint to record the content phase
  So that edited localized slides are accepted instead of rejected with 422

  Scenario: Send-back to content records the content phase
    Given a carousel at the final-review interrupt
    When the reviewer revises with structured feedback target_phase "content"
    Then the final_review node records current_phase "content"
    And the send_back_target_phase remains set to "content"

  Scenario: Send-back to a non-content phase is preserved
    Given a carousel at the final-review interrupt
    When the reviewer revises with structured feedback target_phase "images"
    Then the final_review node records current_phase "images"

  Scenario: Approval keeps the final-review phase and clears the send-back target
    Given a carousel at the final-review interrupt with a stale send_back_target_phase
    When the reviewer approves for publish
    Then the final_review node records current_phase "final_review"
    And the send_back_target_phase is cleared

  Scenario: A bogus send-back target never reaches current_phase
    Given a carousel at the final-review interrupt
    When the reviewer revises with a target_phase outside the workflow phases
    Then the final_review node falls back to current_phase "final_review"
