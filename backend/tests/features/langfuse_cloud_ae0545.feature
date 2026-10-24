Feature: Tracing goes to Langfuse Cloud and the Langfuse stack leaves the droplet (AE-0545)
  The self-hosted Langfuse stack (web, worker, ClickHouse, MinIO) was the largest memory
  consumer on the 3916 MiB droplet and crash-looped under its cap. Pedro moved tracing to
  Langfuse Cloud (Hobby tier): the backend sends traces there when both Cloud keys are set
  and traces nothing, quietly, when they are not.

  Scenario: Tracing is disabled when the Langfuse keys are not set
    Given no Langfuse public key and no secret key
    When the backend starts tracing
    Then no Langfuse client or callback handler is created

  Scenario: Tracing stays disabled when only one Langfuse key is set
    Given only the public key, or only the secret key
    When the backend starts tracing
    Then no Langfuse client or callback handler is created

  Scenario: Tracing reports to Langfuse Cloud when both keys are set
    Given both Langfuse keys and the Cloud host
    When the backend starts tracing
    Then the Langfuse client is created for that host with those keys

  Scenario: The backend defaults to the Langfuse Cloud host
    Given no LANGFUSE_HOST setting
    Then the backend's Langfuse host is https://cloud.langfuse.com

  Scenario: The Langfuse stack no longer runs on the droplet
    Given the production compose file
    Then it has no Langfuse web, worker, ClickHouse, MinIO or Langfuse database init service, and no volume of theirs
    And the backend's Langfuse host defaults to Langfuse Cloud

  Scenario: The deploy wires the Langfuse Cloud keys without requiring them
    Given the deploy workflow
    Then the backend env takes its Langfuse keys from the LANGFUSE_CLOUD_PUBLIC_KEY and LANGFUSE_CLOUD_SECRET_KEY secrets
    And its host from the LANGFUSE_CLOUD_HOST variable, defaulting to https://cloud.langfuse.com
    And no self-hosted Langfuse secret is written
    And an empty Langfuse key does not stop the deploy

  Scenario: The deploy removes the old Langfuse containers
    Given the deploy workflow
    Then the stack is taken down with --remove-orphans
