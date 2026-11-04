Feature: Fast-role calls leave the reasoning model room to answer (AE-0609)

  AE-0607 found that a bound max_tokens reaches the endpoint as
  max_completion_tokens and replaces the model's 32000 default, and that the
  fast models spend that budget on reasoning before they write the answer.
  Only four call sites bind a cap. Slide drafting (32000) and the copy-budget
  fit (32000) leave room. Cover prompt ideas (1500) and palette generation
  (2000) did not: prod reasoning runs up to about 6k tokens. Both now run with
  32000. Their deadlines, validators and the retry queue are unchanged.

  Scenario Outline: The provider receives the call's token budget
    Given the fast model is the OpenCode Go chat model with its 32000 default
    When the <call> model is called
    Then the request body asks for max_completion_tokens 32000
    And the request body has no max_tokens

    Examples:
      | call        |
      | cover ideas |
      | palette     |

  Scenario: A prompt YAML's cap that no code binds stays off the wire
    Given the outline YAML says max_tokens 2048
    When the outline agent calls the OpenCode Go chat model
    Then the request body asks for max_completion_tokens 32000

  Scenario Outline: An empty primary answer moves the call to the fallback
    Given the fast queue's first model spends its budget on reasoning and answers nothing
    And the next model answers
    When the <call> model is called
    Then the answer is the next model's
    And both models received the token budget

    Examples:
      | call        |
      | cover ideas |
      | palette     |

  Scenario: An empty cover ideas answer is a logged model failure
    Given every model of the role answers nothing
    When the cover ideas are requested
    Then cover_prompt_ideas_call_failed names EmptyIdeasAnswerError for each attempt
    And the ideas are unavailable

  Scenario: An empty palette answer is a logged model failure
    Given every model of the role answers nothing
    When a palette is generated
    Then palette_generation_call_failed names EmptyPaletteAnswerError
    And the generator is unavailable

  Scenario: A whitespace answer counts as empty
    Given the model answers only whitespace
    When the cover ideas or palette model is called
    Then the call raises its named empty-answer error

  Scenario: A failed palette call is logged with its error
    Given the fast model raises an error
    When a palette is generated
    Then palette_generation_call_failed names that error
    And the generator is unavailable

  Scenario Outline: The call reaches Langfuse as a generation
    Given Langfuse is configured
    When the <call> model is called
    Then the chat model runs with the Langfuse callback and the phase's run name

    Examples:
      | call        |
      | cover ideas |
      | palette     |
