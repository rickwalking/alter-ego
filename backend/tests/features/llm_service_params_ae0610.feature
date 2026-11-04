Feature: LLMService sends the requested temperature and records its calls (AE-0610)

  LLMService.generate passed temperature and max_tokens through with_config,
  which puts them in the run config and not in the request, so every caller ran
  at 0.7 and 32000. No caller passes max_tokens, and every model behind this
  service spends its token budget on reasoning before it answers (AE-0607), so
  the argument is gone and every call keeps the 32000 default. The calls also
  recorded no Langfuse generation.

  Scenario Outline: The provider receives the requested temperature
    Given the LLM service runs on the <route> chat model
    When a caller asks for temperature <temperature>
    Then the request body says temperature <temperature>
    And the request body asks for max_completion_tokens 32000

    Examples:
      | route     | temperature |
      | role-less | 0.2         |
      | role-less | 0.3         |
      | fast      | 0.8         |

  Scenario: A caller that names no temperature sends the default
    Given the LLM service runs on the fast chat model
    When a caller asks for no temperature
    Then the request body says temperature 0.7

  Scenario: A streamed call receives the requested temperature
    Given the LLM service runs on the role-less chat model
    When a caller streams with temperature 0.3
    Then the request body says temperature 0.3
    And the call reaches Langfuse as one generation

  Scenario: A caller cannot set a token cap
    Given the LLM service runs on the role-less chat model
    When a caller asks for max_tokens 777
    Then the call is refused before it reaches the provider

  Scenario: An empty answer moves the call down the fast queue
    Given the fast queue's first model answers nothing
    And the next model answers
    When a caller asks for temperature 0.2
    Then the caller gets the next model's answer
    And both models got temperature 0.2 and max_completion_tokens 32000

  Scenario: An empty answer moves the routed call to its fallback
    Given the routed fast model's primary answers nothing
    And the fallback answers
    When a caller asks for temperature 0.2
    Then the caller gets the fallback's answer

  Scenario: An empty answer from the last routed model is a model failure
    Given the routed fast model and its fallback answer nothing
    When a caller asks for an answer
    Then the call fails with an empty answer error

  Scenario Outline: An empty answer with no fallback is a model failure
    Given the role-less chat model answers <answer>
    When a caller asks for an answer
    Then the call fails with an empty answer error

    Examples:
      | answer  |
      | nothing |
      | blank   |

  Scenario: The call reaches Langfuse as a generation
    Given a Langfuse handler is configured
    When a caller asks for an answer on the fast queue
    Then the handler sees one generation named after the active phase
    And the generation is tagged with the actual model

  Scenario: Without Langfuse the call runs with no callbacks
    Given no Langfuse handler is configured
    When a caller asks for an answer
    Then the caller gets the answer

  Scenario Outline: A blog AI call is traced with its phase, agent and content type
    When the blog <call> runs
    Then the LLM call ran in a trace with phase <phase>, agent blog_ai and content type blog_post

    Examples:
      | call    | phase      |
      | suggest | ai_suggest |
      | improve | ai_improve |

  Scenario Outline: A blog AI call records the user who asked for it
    When the blog <call> runs for user u-1
    Then the LLM call ran in a trace with user u-1

    Examples:
      | call        |
      | suggest     |
      | improve     |
      | translation |

  Scenario: A blog translation with no user keeps the unknown fallback
    When a background job translates a blog post
    Then the LLM call ran in a trace with user unknown

  Scenario Outline: A refinement names its own phase
    When a <refinement> is refined
    Then the LLM call names phase <phase>, agent carousel_refinement and content type carousel
    And it names the project id
    And it names the project owner as the user

    Examples:
      | refinement      | phase         |
      | slide image     | refine_image  |
      | carousel design | refine_design |

  Scenario: A refinement of a project with no owner names no user
    When a slide image of a project with no owner is refined
    Then the LLM call names no user

  Scenario: A conversation title names its own phase
    When a conversation title is generated
    Then the LLM call names phase conversation_title, agent conversation_title and content type chat
    And it names the conversation id as the project id
    And it names the signed-in user

  Scenario: The service opens the phase the call names
    Given a Langfuse handler is configured
    When a caller names phase refine_design for project p-1
    Then the generation is named "carousel.refine_design"
    And its trace carries the phase, agent, content type, project id and user id

  Scenario: A call that names no user keeps the unknown fallback
    Given a Langfuse handler is configured
    When a caller names a phase and no user
    Then its trace records the user as unknown

  Scenario: A failing call closes the phase it named
    Given the role-less chat model answers nothing
    When a caller names a phase
    Then the call fails with an empty answer error
    And the trace records the error

  Scenario Outline: An empty answer on a blog AI route is a typed 503
    Given the model answers nothing
    When the editor POSTs /blog-posts/{id}/<route>
    Then the response is 503 with code provider_unavailable and a safe message
    And the body names no model
    And the post records no AI action

    Examples:
      | route      |
      | ai-suggest |
      | ai-improve |

  Scenario: An empty answer on ai-suggest stores no suggestion
    Given the model answers nothing
    When the editor POSTs /blog-posts/{id}/ai-suggest
    Then the post has no stored suggestion

  Scenario Outline: A bad request on a blog AI route stays a 400
    Given the AI service rejects the request
    When the editor POSTs /blog-posts/{id}/<route>
    Then the response is 400

    Examples:
      | route      |
      | ai-suggest |
      | ai-improve |
