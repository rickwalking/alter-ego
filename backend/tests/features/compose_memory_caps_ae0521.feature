Feature: Every long-running production container has a memory cap (AE-0521)
  The droplet has 3916 MiB of RAM and runs the website, the carousel exports and
  the observability stack side by side. An uncapped container that grows can push
  the kernel OOM killer onto the website, so each long-running service carries a
  memory limit sized from the measured peak, and the observability stack is shrunk
  to make room for the carousel generation worker (Pedro, 2026-10-23).

  Scenario: Every long-running service has a memory limit
    Given the production compose file
    When every service except the one-shot jobs is read
    Then each one declares a memory limit

  Scenario: A service without a memory limit is reported
    Given a compose document with uncapped services under any restart policy
    When the caps are checked
    Then every uncapped service except the one-shot jobs is reported

  Scenario: Reservations never exceed their limits
    Given the production compose file
    When the services with a memory reservation are read
    Then each reservation is smaller than the service limit

  Scenario: The backend limit covers the measured HD export peak
    Given the backend runs the carousel HD exports in process
    When its memory limit is read
    Then it is at least the measured HD run peak plus 30 percent
    And the backend reserves memory for the website

  Scenario: Langfuse web keeps its Node heap below its container limit
    Given the production compose file
    When the langfuse service is read
    Then it is capped at 1280 MiB
    And its Node heap limit is at least 1024 MiB
    And its Node heap limit leaves room under that cap

  Scenario: ClickHouse caps its server memory below its container limit
    Given the production compose file and the ClickHouse low-memory config
    When the clickhouse service and its server memory ratio are read
    Then the container is capped at 640 MiB
    And the server memory ratio is at most 0.75
