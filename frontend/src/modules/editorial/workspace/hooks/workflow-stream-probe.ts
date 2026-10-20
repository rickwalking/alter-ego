/** AE-0440: auth probe that follows an editorial workflow stream error. */

import { z } from "zod";
import { API_ENDPOINTS, HTTP_STATUS } from "@/constants/api";
import { WORKFLOW_STREAM_PROBE_OUTCOME } from "@/constants/editorial-workflow";
import { ApiError, apiCall } from "@/lib/api-client";
import type { EditorialWorkflowState } from "@/modules/editorial/workspace/types-ai";
import type { WorkflowStreamProbeResult } from "./types";

const workflowStateProbeSchema = z.custom<EditorialWorkflowState>(
  (value) => typeof value === "object" && value !== null,
);

/** Statuses after which reconnecting can never succeed for this tab. */
const AUTH_FAILURE_STATUSES: ReadonlySet<number> = new Set([
  HTTP_STATUS.UNAUTHORIZED,
  HTTP_STATUS.FORBIDDEN,
]);

function outcomeOfError(err: unknown): WorkflowStreamProbeResult {
  if (!(err instanceof ApiError)) {
    return { outcome: WORKFLOW_STREAM_PROBE_OUTCOME.TRANSIENT };
  }
  if (AUTH_FAILURE_STATUSES.has(err.status)) {
    return { outcome: WORKFLOW_STREAM_PROBE_OUTCOME.AUTH_FAILED };
  }
  if (err.status === HTTP_STATUS.NOT_FOUND) {
    return { outcome: WORKFLOW_STREAM_PROBE_OUTCOME.GONE };
  }
  return { outcome: WORKFLOW_STREAM_PROBE_OUTCOME.TRANSIENT };
}

/**
 * GET workflow/state through the api-client. EventSource hides the status of
 * a failed stream; this request does not, and the api-client sends a 401 to
 * the session-expired login (AE-0429/AE-0431) and a 403 to the 403 page.
 */
export async function probeWorkflowStream(
  projectId: string,
): Promise<WorkflowStreamProbeResult> {
  try {
    const state = await apiCall(
      API_ENDPOINTS.CAROUSEL_WORKFLOW_STATE(projectId),
      workflowStateProbeSchema,
    );
    return { outcome: WORKFLOW_STREAM_PROBE_OUTCOME.OK, state };
  } catch (err) {
    return outcomeOfError(err);
  }
}
