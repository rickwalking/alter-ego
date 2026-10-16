Feature: Model queue with a circuit breaker and OpenCode sidecar (AE-0399)
  Each LLM role can run on a queue of models. A per-model circuit breaker
  decides by the failure class whether to retry, debounce, or skip the model,
  and breaker changes go to a send-only Telegram alerts bot.

  Scenario: The first model with a closed breaker answers
    Given a queue of three models that all answer
    When a call is made
    Then only the first model is called

  Scenario: A refused model is skipped at once
    Given the first model answers 403 FreeTierError
    When a call is made
    Then its breaker opens with the fatal cooldown and the second model answers
    And the next call skips the first model without calling it

  Scenario: A usage limit opens the breaker without retries
    Given the first model answers 429 GoUsageLimitError
    When a call is made
    Then it is called once, its breaker opens with the quota cooldown, and the next model answers

  Scenario: Transient errors retry, then open the breaker
    Given the first model fails with 503 every time
    When a call is made
    Then it is tried 3 times with backoff, its breaker opens, and the next model answers

  Scenario: A rate limit is debounced with Retry-After
    Given the first model answers 429 with Retry-After 2 once, then succeeds
    When a call is made
    Then the queue waits 2 seconds and the first model answers

  Scenario: An empty answer is re-rolled before moving on
    Given the first model answers empty every time
    When a call is made
    Then it is tried 3 times and the next model answers, and its breaker stays closed

  Scenario: Only one probe passes a half-open breaker
    Given a breaker whose cooldown has expired
    When two calls arrive
    Then the first probes the model and the second skips it

  Scenario: A failed probe doubles the cooldown
    Given a half-open breaker whose probe fails
    When the breaker reopens
    Then its cooldown is twice the previous one, capped at one hour

  Scenario: All models down fails fast with every state named
    Given every model in the queue is open or failing
    When a call is made
    Then AllModelsUnavailableError names each model's state and the all-down alert fires

  Scenario: The OpenCode sidecar is called with Basic auth and one session per call
    Given a sidecar model "opencode/deepseek-v4.1-flash-free"
    When it answers
    Then a session is created, the message carries the model and the system prompt, and the session is deleted

  Scenario: A sidecar model error keeps the provider status for the breaker
    Given the sidecar reports a 403 FreeTierError from the model
    When the call is classified
    Then it is fatal

  Scenario: Breaker changes are alerted once and all-down is rate-limited
    Given a configured alerts bot
    When a breaker opens and two all-down events arrive within 15 minutes
    Then one open alert and one all-down alert are sent

  Scenario: Without a queue setting the AE-0391 routing is kept
    Given no LLM_MODEL_QUEUE_FAST
    When the fast model is built
    Then it is the routed model with its fallback
