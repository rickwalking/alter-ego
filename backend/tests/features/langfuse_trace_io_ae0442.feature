Feature: Langfuse traces carry input, output and useful names (AE-0442)
  Prod 2026-10-20: 128 traces, 176 spans and 18 events in 24 h had empty
  input AND output; 404 generations were named "ChatOpenAI" and 18 traces had
  an empty name (orphan human-review events). Langfuse v3 derives trace I/O
  from the root observation, so a root span that never sets input/output
  leaves the whole trace blank. This feature pins what every trace records.

  Background:
    Given Langfuse is configured with a fake client

  # --- Phase traces ---------------------------------------------------------

  Scenario: A phase trace records its brief as input and its result as output
    Given a carousel owned by "owner-1" in project "p-1"
    When the "content" phase trace opens with topic "IA", attempt 2 and the fast model queue
    And the phase finishes with 7 slides
    Then the root span is named "workflow_content"
    And the trace is named "workflow_content"
    And the trace input has project_id "p-1", phase "content", topic "IA", attempt 2 and model queue "deepseek-v4.1-flash"
    And the trace output has status "completed" and slide_count 7
    And the root span has the same input and output
    And the trace user is "owner-1", its session is "p-1" and its tags include "phase:content"

  Scenario: A failing phase records a redacted error as output
    Given a phase trace for "content"
    When the phase raises "provider down" after a Telegram bot token in the message
    Then the trace output has status "error" and error_type "RuntimeError"
    And the error message is redacted
    And the exception still reaches the caller

  Scenario: A blog generation trace carries the writer brief and the article summary
    Given a blog post generation phase for post "post-9" and owner "owner-1"
    When the trace opens with the writer brief title "IA no trabalho" and section count 5
    And the writer returns a 5-section article with voice score 82.5
    Then the trace is named "workflow_blog_generation"
    And the trace input has post_id "post-9", title "IA no trabalho" and section_count 5
    And the trace output has status "completed", section_count 5 and voice_score 82.5

  # --- Generations ----------------------------------------------------------

  Scenario: A generation is named after the agent, phase and detail
    Given a phase trace for "content" with content_type "carousel"
    When the content drafter calls the model for slide 3
    Then the runnable config carries run_name "carousel.content slide 3"

  Scenario: A generation outside a phase trace still gets a stable name
    Given no phase trace is active
    When an LLM call asks for the Langfuse runnable config
    Then the runnable config carries run_name "llm.call"

  # --- Review events and nested helpers -------------------------------------

  Scenario: A human review is recorded in a named trace with input and output
    Given a human review approval by "reviewer-1" for project "p-1"
    When the review event is recorded
    Then the trace is named "workflow_review"
    And one "human_review_review_completed" event is recorded inside it
    And the review trace input has the action "approve" and the output has status "recorded"

  Scenario: A nested propagation helper reuses the outer phase span
    Given an outer "blog_section_image" phase trace for post "post-9" and owner "owner-1"
    When the image service propagates "blog_section_image" for the same post
    Then only one span is opened
    And the trace keeps project_id "post-9", user_id "owner-1" and agent_name "blog_images"
    And the trace metadata also has the post_id

  # --- Safety and flushing ---------------------------------------------------

  Scenario: Captured payloads never contain secrets
    Given a phase input with a Telegram bot token and an access_token query value
    When the phase finishes
    Then the captured input redacts the bot token and the access_token
    And the captured output redacts the bot token and the access_token

  Scenario: A phase flush happens even when the phase fails
    Given a phase trace for "images"
    When the phase raises a provider error
    Then the fake Langfuse client is flushed exactly once

  Scenario: A finished background runner flushes Langfuse
    Given a configured Langfuse client
    When a background blog generation run finishes
    Then the client is flushed

  Scenario: A tracing failure never changes the workflow result
    Given a phase trace whose Langfuse span cannot be opened
    When the phase body returns 7 slides
    Then the phase body still returns 7 slides
    And no tracing exception is raised

  Scenario: A flush failure never changes the workflow result
    Given a phase trace whose Langfuse flush fails
    When the phase body returns 7 slides
    Then the phase body still returns 7 slides
    And no tracing exception is raised

  Scenario: A hanging exporter never blocks the workflow
    Given a Langfuse client whose flush hangs on the exporter
    When a background runner requests a tracing flush
    Then the request returns immediately
    And the workflow result is unchanged

  Scenario: A hung flush does not starve a later flush
    Given a Langfuse client whose flush hangs on the exporter
    When another trace requests its own flush
    Then the later flush still reaches the exporter
