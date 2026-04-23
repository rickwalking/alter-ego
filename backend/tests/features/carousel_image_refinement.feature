Feature: Carousel slide image regeneration
  As a carousel author
  I want to ask the agent to regenerate a slide's hero image
  So I can iterate on visuals without rebuilding the entire carousel

  Background:
    Given a completed carousel project with output_dir and 2 slides

  Scenario: Regenerate image with a new prompt
    When the agent regenerates slide 2 with instruction "make it futuristic"
    Then the slide's image_prompt is rewritten by the LLM
    And the new image is generated
    And the slides are re-exported

  Scenario: Missing project is rejected
    When the agent regenerates an image for a non-existent project
    Then a ValueError is raised with "not found"

  Scenario: Missing output_dir is rejected
    Given a project with no output_dir
    When the agent regenerates an image
    Then a ValueError is raised with "output_dir"

  Scenario: Missing slide is rejected
    Given a project with only 1 slide
    When the agent regenerates slide 2
    Then a ValueError is raised with "Slide 2 not found"

  Scenario: Missing image_prompt is rejected
    Given a project with a slide that has no image_prompt
    When the agent regenerates that slide
    Then a ValueError is raised with "no image_prompt"
