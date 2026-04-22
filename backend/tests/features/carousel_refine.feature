Feature: Agent-driven carousel copy refinement
  As a carousel author
  I want to ask the agent to tweak individual copy fields
  So I can iterate on captions, LinkedIn posts, and slides without regenerating

  Background:
    Given a completed carousel project with caption, PT + EN LinkedIn posts, and 6 slides

  Scenario: Shorten the Instagram caption
    When the agent refines target "instagram_caption" with instruction "make it shorter"
    Then the project's caption field is overwritten with the LLM output
    And the project is persisted via update_project

  Scenario: Swap hashtags in the Instagram caption
    When the agent refines target "instagram_caption" with "swap hashtags for tech ones"
    Then the caption reflects the new hashtags

  Scenario: Rewrite the Portuguese LinkedIn post
    When the agent refines target "linkedin_post_pt" with "less formal"
    Then project.linkedin_post_pt contains the new text

  Scenario: Rewrite the English LinkedIn post
    When the agent refines target "linkedin_post_en" with "punchier hook"
    Then project.linkedin_post_en contains the new text

  Scenario: Rewrite a slide heading
    When the agent refines target "slide_heading:2" with "start with a verb"
    Then the second slide's heading is updated
    And update_slide is called for slide_number=2

  Scenario: Rewrite a slide body
    When the agent refines target "slide_body:3" with "use bullet points"
    Then the third slide's body is updated

  Scenario: Unknown target returns an explanation
    When the agent refines target "blog_footer" with "remove it"
    Then no update occurs
    And the response explains the target selector is unknown

  Scenario: Invalid slide number is handled gracefully
    When the agent refines target "slide_heading:not-a-number" with "bold"
    Then no update occurs

  Scenario: Slide number out of range is handled gracefully
    When the agent refines target "slide_heading:99" with "rewrite"
    Then no update occurs
    And the response says the field is empty or target is unknown
