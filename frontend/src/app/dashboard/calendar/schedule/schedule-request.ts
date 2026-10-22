import {
  API_ENDPOINTS,
  CONTENT_TYPES,
  HTTP_METHODS,
  HTTP_STATUS,
} from "@/constants/api";
import { HTTP_HEADER_IF_MATCH } from "@/constants/workflow";
import { authenticatedFetch } from "@/lib/authenticated-fetch";
import type { BlogPost } from "@/modules/publishing";
import { CONTENT_TYPE_HEADER, SCHEDULE_ERROR_CODE_IN_PAST } from "./constants";
import type { ScheduleRequestError, ScheduleRequestResult } from "./types";

async function errorFor(response: Response): Promise<ScheduleRequestError> {
  if (response.status === HTTP_STATUS.CONFLICT) {
    return "versionConflict";
  }
  if (response.status === HTTP_STATUS.UNPROCESSABLE_ENTITY) {
    return "notReady";
  }
  if (response.status !== HTTP_STATUS.BAD_REQUEST) {
    return "failed";
  }
  const body = (await response.json().catch(() => null)) as {
    detail?: unknown;
  } | null;
  return body?.detail === SCHEDULE_ERROR_CODE_IN_PAST ? "timeInPast" : "failed";
}

/**
 * POST the schedule for an approved post (`scheduled_publish_at` in UTC), with
 * the post's lock version as `If-Match` so a post changed meanwhile is refused.
 */
export async function requestSchedule(
  post: BlogPost,
  at: Date,
): Promise<ScheduleRequestResult> {
  try {
    const response = await authenticatedFetch(
      API_ENDPOINTS.BLOG_SCHEDULE(post.id),
      {
        method: HTTP_METHODS.POST,
        headers: {
          [CONTENT_TYPE_HEADER]: CONTENT_TYPES.JSON,
          [HTTP_HEADER_IF_MATCH]: String(post.lock_version),
        },
        body: JSON.stringify({ scheduled_publish_at: at.toISOString() }),
      },
    );
    if (!response.ok) {
      return { ok: false, error: await errorFor(response) };
    }
    return { ok: true, post: (await response.json()) as BlogPost };
  } catch {
    return { ok: false, error: "failed" };
  }
}
