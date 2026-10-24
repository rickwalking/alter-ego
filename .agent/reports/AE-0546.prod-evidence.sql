-- AE-0546 prod evidence for carousel 5350e0ca-ad31-40a1-9e50-70852f1ee484 (read-only).
-- Run with: docker compose exec -T postgres psql -U <user> -d <db> -v ON_ERROR_STOP=1 -f - < this file
-- Every statement runs inside a READ ONLY transaction that is rolled back.
\pset null '<NULL>'
BEGIN TRANSACTION READ ONLY;

-- 1. The carousel-origin blog row (the caption's distribution home): when it was
--    created and whether its distribution was still {} before 03:13 UTC 2026-10-24.
SELECT id,
       origin,
       status,
       created_at,
       updated_at,
       lock_version,
       created_at < TIMESTAMPTZ '2026-10-24 03:13:00+00' AS created_before_approve,
       distribution,
       distribution::jsonb = '{}'::jsonb AS distribution_is_empty,
       distribution -> 'caption' AS home_caption_json
FROM blog_posts
WHERE project_id = '5350e0ca-ad31-40a1-9e50-70852f1ee484'
  AND origin = 'carousel'
ORDER BY created_at;

-- 2. The caption column now: NULL versus '' (psql prints both blank without \pset null).
SELECT id,
       caption IS NULL AS caption_is_null,
       caption = '' AS caption_is_empty_string,
       length(caption) AS caption_length,
       workflow_status,
       is_public,
       current_phase,
       lock_version,
       updated_at
FROM carousel_projects
WHERE id = '5350e0ca-ad31-40a1-9e50-70852f1ee484';

-- 3. Every saved caption version: an owner edit or restore that set '' would show up
--    here (the copy edit and the restore always record one version per field).
SELECT version_number,
       created_at,
       author_id,
       change_summary,
       snapshot ->> 'restored_from' AS restored_from,
       length(snapshot ->> 'text') AS caption_length,
       (snapshot ->> 'text') = '' AS caption_is_empty_string
FROM content_versions
WHERE content_id = '5350e0ca-ad31-40a1-9e50-70852f1ee484'
  AND content_type = 'carousel_copy'
  AND snapshot ->> 'field' = 'caption'
ORDER BY version_number;

ROLLBACK;
