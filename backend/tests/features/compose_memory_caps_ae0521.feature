Feature: Every long-running production container has a memory cap (AE-0521)
  The droplet has 3916 MiB of RAM and runs the website, the carousel exports and
  its support services side by side. An uncapped container that grows can push
  the kernel OOM killer onto the website, so each long-running service carries a
  memory limit sized from the measured peak, and the self-hosted Langfuse stack moved to
  Langfuse Cloud to make room for the carousel generation worker (Pedro, 2026-10-24).

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
    Given the backend still runs the dashboard exports, finalize and refinement renders
    When its memory limit is read
    Then it is at least the measured HD run peak plus 30 percent
    And the backend reserves memory for the website

  Scenario: The generation worker limit covers the measured HD export peak
    Given the generation worker runs the carousel HD exports
    When its memory limit is read
    Then it is at least the measured HD run peak plus 30 percent, with no swap
