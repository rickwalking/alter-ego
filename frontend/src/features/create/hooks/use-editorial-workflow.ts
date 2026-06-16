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
import type { EditorialWorkflowState } from "@/modules/publishing";
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

interface StartWorkflowInput {
  topic: string;
  audience: string;
  brief: string;
  sources: Array<{ title: string; content: string; source_type?: string }>;
  personaId?: string;
}

export type { EditorialReviseOptions };

export function useEditorialWorkflow(projectId: string) {
  const t = useTranslations("editorialWorkflow.errors");
  const [state, setState] = useState<EditorialWorkflowState | null>(null);
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

  useEffect(() => {
    void refreshState();
  }, [refreshState]);

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
    start,
    resume,
    refreshState,
    approve: (options?: EditorialReviseOptions) =>
      resume(EDITORIAL_REVIEW_ACTIONS.APPROVE, undefined, options),
    revise: (feedback: string, options?: EditorialReviseOptions) =>
      resume(EDITORIAL_REVIEW_ACTIONS.REVISE, feedback, options),
    awaitingHumanReview:
      state?.phase_status === WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
    hasActiveWorkflow: Boolean(state?.current_phase),
  };
}
