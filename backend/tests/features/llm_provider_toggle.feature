Feature: Configurable backend chat LLM provider (AE-0285)
  The backend chat LLM (carousel generation, alter-ego chat agent, RAG agent) is
  selectable between Anthropic Claude and GLM 5.2 (via the OpenCode Go
  OpenAI-compatible endpoint) so generation can run on GLM to cut Anthropic spend,
  with Anthropic kept as a safe fallback.

  Scenario: GLM provider selected with a key
    Given llm_provider is "glm" and a GLM api key is set
    When the chat model is built
    Then it is an OpenAI-compatible client pointed at the GLM base_url and model

  Scenario: Anthropic provider selected
    Given llm_provider is "anthropic"
    When the chat model is built
    Then it is a ChatAnthropic using the configured Claude model

  Scenario: GLM selected but no key (CI / prod not yet configured)
    Given llm_provider is "glm" and the GLM api key is empty
    When the chat model is built
    Then it falls back to ChatAnthropic
    And a warning is logged so the misconfiguration is visible

  Scenario: GLM requests carry the OpenCode session header (AE-0330)
    Given llm_provider is "glm" and a GLM api key is set
    When the chat model sends a request to the OpenCode Go endpoint
    Then the request carries an "x-opencode-session" header
    And it identifies itself with an "alter-ego/<version>" user agent
    And OpenCode Go therefore does not reject it with 400 MissingSessionID

  Scenario: the session id is stable for the life of a client (AE-0330)
    Given a GLM chat model has been built
    When two requests are made through it
    Then both carry the same session id
    And a separately built client uses a different session id

  Scenario: the OpenCode headers do not leak onto Anthropic (AE-0330)
    Given llm_provider is "anthropic"
    When the chat model is built
    Then it carries no OpenCode session header

  Scenario: provider swap is transparent to consumers
    Given any provider is configured
    When a consumer requests the chat model
    Then it receives a LangChain BaseChatModel with no provider-specific coupling
