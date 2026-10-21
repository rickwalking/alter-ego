/** Editorial carousel workflow hook with SSE updates. */

import { useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { API_ENDPOINTS, HTTP_METHODS, HTTP_STATUS } from "@/constants/api";
import { EDITORIAL_REVIEW_ACTIONS } from "@/constants/blog-ai";
import {
  EDITORIAL_WORKFLOW_TRANSPORT_MODE,
  type EditorialWorkflowTransportMode,
} from "@/constants/editorial-workflow";
import { WORKFLOW_PHASE_STATUS } from "@/constants/workflow";
import type { EditorialWorkflowState } from "@/modules/editorial/workspace/types-ai";
import { authenticatedFetch } from "@/lib/authenticated-fetch";
import {
  appendUniquePhase,
  readApiError,
} from "./use-editorial-workflow-utils";
import {
  useEditorialWorkflowResume,
  type EditorialReviseOptions,
} from "./use-editorial-workflow-resume";
import { useEditorialWorkflowSse } from "./use-editorial-workflow-sse";
import type {
  RecordedResume,
  StartWorkflowInput,
  UseEditorialWorkflowOptions,
} from "./types";

export type { EditorialReviseOptions };

/**
 * AE-0414 (B02): an edits-only revise (content manual fixes, design recovery)
 * carries the reviewer's slide edits and no feedback. Its callers fire and
 * forget it, so a rejection would surface as an uncaught page error; the
 * failure is already shown through the hook's translated ``error``.
 */
function isEditsOnlyRevise(
  feedback: string,
  options?: EditorialReviseOptions,
): boolean {
  return !feedback.trim() && (options?.editedLocalizedSlides?.length ?? 0) > 0;
}

/** The action that started the running phase, or null when unknown. */
function resolveRunningAction(
  state: EditorialWorkflowState | null,
  lastResume: RecordedResume | null,
): string | null {
  if (
    state?.phase_status !== WORKFLOW_PHASE_STATUS.IN_PROGRESS ||
    lastResume?.phase !== state.current_phase
  ) {
    return null;
  }
  return lastResume.action;
}

export function useEditorialWorkflow(
  projectId: string,
  options?: UseEditorialWorkflowOptions,
) {
  const t = useTranslations("editorialWorkflow.errors");
  const initialFetch = options?.initialFetch ?? true;
  const [state, setState] = useState<EditorialWorkflowState | null>(null);
  // AE-0415 (B27): which review action started the current run, and on which
  // phase, so the running banner can name the phase that is really running.
  const [lastResume, setLastResume] = useState<RecordedResume | null>(null);
  const [phaseEvents, setPhaseEvents] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [transportMode, setTransportMode] =
    useState<EditorialWorkflowTransportMode>(
      EDITORIAL_WORKFLOW_TRANSPORT_MODE.SSE,
    );

  const refreshState =
    useCallback(async (): Promise<EditorialWorkflowState | null> => {
      try {
        const response = await authenticatedFetch(
          API_ENDPOINTS.CAROUSEL_WORKFLOW_STATE(projectId),
        );
        if (response.status === HTTP_STATUS.NOT_FOUND) {
          return null;
        }
        if (!response.ok) {
          return null;
        }
        const workflowState = (await response.json()) as EditorialWorkflowState;
        setState(workflowState);
        if (workflowState.current_phase) {
          setPhaseEvents((prev) =>
            appendUniquePhase(prev, workflowState.current_phase),
          );
        }
        return workflowState;
      } catch {
        return null;
      }
    }, [projectId]);

  const {
    enterPollingFallback,
    stopPollingFallback,
    reconnectLiveUpdates,
    transportModeRef,
    workflowStateRef,
  } = useEditorialWorkflowSse({
    projectId,
    sseEnabled: Boolean(state?.current_phase),
    state,
    transportMode,
    setState,
    setPhaseEvents,
    setTransportMode,
    setError,
    refreshState,
  });

  // AE-0415 (B30): a project that never started its workflow has no state
  // (GET answers 404); callers that know this skip the request.
  useEffect(() => {
    if (!initialFetch) {
      return;
    }
    void refreshState();
  }, [initialFetch, refreshState]);

  const { resume } = useEditorialWorkflowResume({
    projectId,
    lockVersion: state?.lock_version,
    translateError: t,
    workflowStateRef,
    transportModeRef,
    refreshState,
    setState,
    setPhaseEvents,
    setLoading,
    setError,
    enterPollingFallback,
    stopPollingFallback,
  });

  const start = useCallback(
    async (input: StartWorkflowInput): Promise<EditorialWorkflowState> => {
      setLoading(true);
      setError(null);
      try {
        const response = await authenticatedFetch(
          API_ENDPOINTS.CAROUSEL_WORKFLOW_START(projectId),
          {
            method: HTTP_METHODS.POST,
            body: JSON.stringify({
              topic: input.topic,
              audience: input.audience,
              brief: input.brief,
              sources: input.sources,
              persona_id: input.personaId,
            }),
          },
        );
        if (!response.ok) {
          throw new Error(await readApiError(response, t("startFailed")));
        }
        const workflowState = (await response.json()) as EditorialWorkflowState;
        setState(workflowState);
        workflowStateRef.current = workflowState;
        if (workflowState.current_phase) {
          setPhaseEvents((prev) =>
            appendUniquePhase(prev, workflowState.current_phase),
          );
        }
        return workflowState;
      } catch (err) {
        const message = err instanceof Error ? err.message : t("startUnknown");
        setError(message);
        await refreshState();
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [projectId, refreshState, t, workflowStateRef],
  );

  return {
    state,
    phaseEvents,
    loading,
    error,
    transportMode,
    reconnectLiveUpdates,
    start,
    resume,
    refreshState,
    approve: (reviseOptions?: EditorialReviseOptions) => {
      setLastResume({
        action: EDITORIAL_REVIEW_ACTIONS.APPROVE,
        phase: state?.current_phase ?? "",
      });
      return resume(EDITORIAL_REVIEW_ACTIONS.APPROVE, undefined, reviseOptions);
    },
    revise: (
      feedback: string,
      reviseOptions?: EditorialReviseOptions,
    ): Promise<EditorialWorkflowState | null> => {
      setLastResume({
        action: EDITORIAL_REVIEW_ACTIONS.REVISE,
        phase: state?.current_phase ?? "",
      });
      const pending = resume(
        EDITORIAL_REVIEW_ACTIONS.REVISE,
        feedback,
        reviseOptions,
      );
      return isEditsOnlyRevise(feedback, reviseOptions)
        ? pending.catch(() => null)
        : pending;
    },
    runningAction: resolveRunningAction(state, lastResume),
    awaitingHumanReview:
      state?.phase_status === WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
    hasActiveWorkflow: Boolean(state?.current_phase),
  };
}
