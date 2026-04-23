Feature: Carousel design refinement via CSS overrides
  As a carousel author
  I want to tweak layout, spacing, or sizing with natural language
  So I can polish the visual design without regenerating images

  Background:
    Given a completed carousel project with output_dir and 2 slides

  Scenario: Apply a CSS override and re-export
    When the agent refines design with instruction "make images bigger"
    Then the LLM generates CSS overrides
    And design_overrides.css is written to the output directory
    And the slides are re-exported

  Scenario: Markdown fences are stripped from LLM output
    When the LLM returns CSS wrapped in ```css fences
    Then the fences are removed before writing to design_overrides.css

  Scenario: Missing project is rejected
    When the agent refines design for a non-existent project
    Then a ValueError is raised with "not found"

  Scenario: Missing output_dir is rejected
    Given a project with no output_dir
    When the agent refines design
    Then a ValueError is raised with "output_dir"

  Scenario: No slides is rejected
    Given a project with no slides
    When the agent refines design
    Then a ValueError is raised with "no slides"
