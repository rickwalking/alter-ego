/** Resume/approve/revise actions for editorial workflow hook. */

import { useCallback } from "react";
import { API_ENDPOINTS, HTTP_METHODS, HTTP_STATUS } from "@/constants/api";
import {
  EDITORIAL_WORKFLOW_CONFLICT_CODES,
  EDITORIAL_WORKFLOW_TRANSPORT_MODE,
} from "@/constants/editorial-workflow";
import { WORKFLOW_PHASE_STATUS } from "@/constants/workflow";
import type {
  EditorialWorkflowState,
  LocalizedSlideReview,
} from "@/modules/editorial/workspace/types-ai";
import { authenticatedFetch } from "@/lib/authenticated-fetch";
import {
  appendUniquePhase,
  isResumeAcceptedResponse,
  isResumeClientErrorStatus,
  isResumeTransportFailure,
  isWorkflowReady,
  readApiError,
  waitUntilWorkflowReadyWithTransport,
} from "./use-editorial-workflow-utils";
import type {
  EditorialReviseOptions,
  EditorialWorkflowResumeAcceptedResponse,
  UseEditorialWorkflowResumeParams,
} from "./types";

export type { EditorialReviseOptions } from "./types";

export function useEditorialWorkflowResume({
  projectId,
  lockVersion,
  translateError,
  workflowStateRef,
  transportModeRef,
  refreshState,
  setState,
  setPhaseEvents,
  setLoading,
  setError,
  enterPollingFallback,
  stopPollingFallback,
}: UseEditorialWorkflowResumeParams) {
  const resume = useCallback(
    async (
      action: string,
      feedback?: string,
      options?: EditorialReviseOptions,
    ): Promise<EditorialWorkflowState> => {
      setLoading(true);
      setError(null);
      setState((prev) => {
        if (!prev || isWorkflowReady(prev)) {
          return prev;
        }
        const next = {
          ...prev,
          phase_status: WORKFLOW_PHASE_STATUS.IN_PROGRESS,
        };
        workflowStateRef.current = next;
        return next;
      });

      const preferSseTransport = (): boolean =>
        transportModeRef.current === EDITORIAL_WORKFLOW_TRANSPORT_MODE.SSE;

      // AE-0310/AE-0315: each machine-readable 409 cause gets distinct copy
      // instead of surfacing the raw machine code.
      const resolveResumeErrorMessage = (message: string): string => {
        if (
          message === EDITORIAL_WORKFLOW_CONFLICT_CODES.REVISION_CAP_EXCEEDED
        ) {
          return translateError("revisionCapExceeded");
        }
        if (message === EDITORIAL_WORKFLOW_CONFLICT_CODES.VERSION_CONFLICT) {
          return translateError("versionConflict");
        }
        if (message === EDITORIAL_WORKFLOW_CONFLICT_CODES.RUN_IN_PROGRESS) {
          return translateError("runInProgress");
        }
        return message;
      };

      const waitForReadyState =
        async (): Promise<EditorialWorkflowState | null> =>
          waitUntilWorkflowReadyWithTransport(
            () => workflowStateRef.current,
            refreshState,
            { preferSse: preferSseTransport() },
          );

      const finalizeResume = async (
        workflowState: EditorialWorkflowState | null,
      ): Promise<EditorialWorkflowState> => {
        if (!workflowState) {
          throw new Error(translateError("resumeFailed"));
        }
        setState(workflowState);
        workflowStateRef.current = workflowState;
        if (workflowState.current_phase) {
          setPhaseEvents((prev) =>
            appendUniquePhase(prev, workflowState.current_phase),
          );
        }
        if (isWorkflowReady(workflowState)) {
          if (
            workflowState.phase_status === WORKFLOW_PHASE_STATUS.AWAITING_HUMAN
          ) {
            stopPollingFallback();
          }
          return workflowState;
        }
        enterPollingFallback();
        const ready = await waitForReadyState();
        if (ready && isWorkflowReady(ready)) {
          setState(ready);
          workflowStateRef.current = ready;
          if (ready.phase_status === WORKFLOW_PHASE_STATUS.AWAITING_HUMAN) {
            stopPollingFallback();
          }
          return ready;
        }
        throw new Error(translateError("resumeFailed"));
      };

      try {
        let resolvedLockVersion = lockVersion;
        if (resolvedLockVersion === undefined) {
          const refreshed = await refreshState();
          resolvedLockVersion = refreshed?.lock_version;
        }
        const payload: {
          action: string;
          feedback?: string;
          expected_version: number;
          structured_feedback?: {
            target_phase?: string;
            edited_text?: string;
            edited_localized_slides?: LocalizedSlideReview[];
          };
        } = {
          action,
          expected_version: resolvedLockVersion ?? 1,
        };
        if (feedback !== undefined) {
          payload.feedback = feedback;
        }
        if (
          options?.targetPhase ||
          options?.editedText ||
          options?.editedLocalizedSlides?.length
        ) {
          payload.structured_feedback = {};
          if (options.targetPhase) {
            payload.structured_feedback.target_phase = options.targetPhase;
          }
          if (options.editedText) {
            payload.structured_feedback.edited_text = options.editedText;
          }
          if (options.editedLocalizedSlides?.length) {
            payload.structured_feedback.edited_localized_slides =
              options.editedLocalizedSlides;
          }
        }

        let response: Response;
        try {
          response = await authenticatedFetch(
            API_ENDPOINTS.CAROUSEL_WORKFLOW_RESUME(projectId),
            {
              method: HTTP_METHODS.POST,
              body: JSON.stringify(payload),
            },
          );
        } catch {
          enterPollingFallback();
          return finalizeResume(await waitForReadyState());
        }

        if (response.status === HTTP_STATUS.ACCEPTED) {
          const accepted =
            (await response.json()) as EditorialWorkflowResumeAcceptedResponse;
          if (!isResumeAcceptedResponse(accepted)) {
            throw new Error(translateError("resumeFailed"));
          }
          setState((prev) => {
            const next =
              prev && isWorkflowReady(prev)
                ? { ...prev, lock_version: accepted.lock_version }
                : prev
                  ? {
                      ...prev,
                      lock_version: accepted.lock_version,
                      phase_status:
                        accepted.phase_status as import("@/modules/editorial/workspace/types-ai").WorkflowPhaseStatus,
                    }
                  : prev;
            workflowStateRef.current = next;
            return next;
          });
          const current = workflowStateRef.current;
          if (current && isWorkflowReady(current)) {
            return finalizeResume(current);
          }
          return finalizeResume(await waitForReadyState());
        }

        if (response.ok) {
          const workflowState =
            (await response.json()) as EditorialWorkflowState;
          return finalizeResume(workflowState);
        }

        if (isResumeClientErrorStatus(response.status)) {
          const detail = await readApiError(
            response,
            translateError("resumeFailed"),
          );
          if (
            response.status === HTTP_STATUS.CONFLICT &&
            detail === EDITORIAL_WORKFLOW_CONFLICT_CODES.RUN_IN_PROGRESS
          ) {
            // AE-0315: a run-in-progress 409 renders the banner, not a
            // toast — refresh pulls run_started_at/run_stage so the banner
            // reconstructs from state.
            const refreshed = await refreshState();
            if (refreshed) {
              setState(refreshed);
              workflowStateRef.current = refreshed;
              return refreshed;
            }
          }
          throw new Error(resolveResumeErrorMessage(detail));
        }

        if (isResumeTransportFailure(response.status)) {
          enterPollingFallback();
          return finalizeResume(await waitForReadyState());
        }

        throw new Error(
          resolveResumeErrorMessage(
            await readApiError(response, translateError("resumeFailed")),
          ),
        );
      } catch (err) {
        const message =
          err instanceof Error ? err.message : translateError("resumeUnknown");
        setError(message);
        await refreshState();
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [
      enterPollingFallback,
      lockVersion,
      projectId,
      refreshState,
      setError,
      setLoading,
      setPhaseEvents,
      setState,
      stopPollingFallback,
      translateError,
      transportModeRef,
      workflowStateRef,
    ],
  );

  return { resume };
}
