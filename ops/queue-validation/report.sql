\pset format unaligned
\pset fieldsep '\t'
\echo generation_runs_by_status
SELECT kind, status, count(*) FROM generation_runs GROUP BY kind, status ORDER BY kind, status;
\echo autopilot_runs_by_state
SELECT state, coalesce(state_reason, ''), count(*) FROM autopilot_runs GROUP BY state, state_reason ORDER BY state;
\echo ready_notices_per_run
SELECT aggregate_id, count(*) FROM event_outbox WHERE event_type = 'content.autopilot.ready_for_owner' GROUP BY aggregate_id ORDER BY aggregate_id;
\echo duplicate_ready_notices
SELECT count(*) FROM (SELECT aggregate_id FROM event_outbox WHERE event_type = 'content.autopilot.ready_for_owner' GROUP BY aggregate_id HAVING count(*) > 1) d;
\echo artifact_builds_per_project
SELECT project_id, status, count(*), count(DISTINCT artifact_version) FROM carousel_artifact_builds GROUP BY project_id, status ORDER BY project_id, status;
\echo duplicate_builds_of_one_version
SELECT count(*) FROM (SELECT project_id, artifact_version FROM carousel_artifact_builds GROUP BY project_id, artifact_version HAVING count(*) > 1) d;
\echo generation_run_attempts
SELECT dedupe_key, status, attempts, phase_attempts::text, coalesce(last_error_code, '') FROM generation_runs ORDER BY created_at;
