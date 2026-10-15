Feature: Phase traces, loopback healthchecks and a heartbeat no run blocks
  AE-0390: prod 2026-10-15. An autopilot carousel had 10 GLM generations in
  3 Langfuse traces; only workflow_research carried metadata, outline and
  content had none, one trace had no name and no trace had tags. The frontend
  container was "unhealthy" 1,201 times because its probe hit localhost, which
  busybox wget resolved to [::1]. The run heartbeat timed out on the project
  row lock twice per phase because the run kept its phase-sync UPDATE
  uncommitted through finalize, review events, SSE and both stage beats.

  Background:
    Given Langfuse is configured

  # --- Langfuse phase traces ------------------------------------------------

  Scenario Outline: A resumed phase runs its LLM calls in a named, tagged trace
    Given a carousel owned by "owner-1" resumed through the HTTP run wrapper
    When the <phase> phase calls the LLM
    Then the call runs inside a trace named "workflow_<phase>"
    And the trace metadata has project_id, phase "<phase>", agent_name "editorial_workflow", user_id "owner-1" and content_type "carousel"
    And the trace tags are "phase:<phase>", "agent:editorial_workflow" and "content:carousel"

    Examples:
      | phase   |
      | outline |
      | content |
      | design  |
      | images  |

  Scenario: Research synthesis at workflow start is traced with the creator
    Given a workflow started by user "creator-1"
    When research synthesis calls the LLM
    Then the call runs inside a trace named "workflow_research"
    And the trace user is "creator-1" and the tags include "phase:research"

  Scenario: The autopilot run traces its phases as the autopilot agent
    Given an autopilot carousel owned by "owner-1" parked at the research gate
    When the autopilot approves the gate and the outline phase calls the LLM
    Then the call runs inside a trace named "workflow_outline"
    And the trace metadata has agent_name "autopilot" and user_id "owner-1"
    And the trace tags are "phase:outline", "agent:autopilot" and "content:carousel"

  Scenario: The autopilot owner autofix is traced with the owner
    Given an autopilot carousel owned by "owner-1" with fixable issues
    When the autofix re-translates through the LLM
    Then the call runs inside a trace named "workflow_owner_autofix" with user_id "owner-1"

  Scenario: Missing attributes never drop a metadata key
    Given no caller scope and no owner
    When a phase trace opens for phase "outline"
    Then all five metadata keys are present, unknown values read "unknown"

  Scenario: Tracing is a no-op without Langfuse
    Given Langfuse is not configured
    When a phase runs
    Then the phase result is unchanged and no trace is opened

  # --- Frontend healthcheck --------------------------------------------------

  Scenario: The frontend image probes the IPv4 loopback
    Given the frontend image healthcheck
    Then it probes "http://127.0.0.1:3000/robots.txt"
    And the Next.js server binds 0.0.0.0

  Scenario: A localhost healthcheck fails CI
    Given a compose healthcheck or Dockerfile HEALTHCHECK that probes localhost
    When the backend:healthcheck-loopback gate runs
    Then it exits 1 and names the file and line

  # --- Run heartbeat ---------------------------------------------------------

  Scenario: The heartbeat succeeds while a phase run is in progress
    Given a carousel run in progress on Postgres
    When the outline phase calls the LLM
    Then a heartbeat from a second session stamps run_heartbeat_at without waiting

  Scenario: The phase sync releases the project row before finalize, events and beats
    Given a carousel run in progress on Postgres
    When the phase run syncs the row to awaiting_human
    Then the sync is committed before the review events, SSE and stage beats
    And a second session can update the row within the run lock timeout
    And no carousel_run_heartbeat_failed warning is logged for the run
