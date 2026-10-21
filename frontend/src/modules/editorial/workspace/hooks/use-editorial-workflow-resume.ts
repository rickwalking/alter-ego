/** Resume/approve/revise actions for editorial workflow hook. */

import { useCallback, useMemo } from "react";
import type { EditorialWorkflowState } from "@/modules/editorial/workspace/types-ai";
import {
  markResumeRunning,
  sendResume,
  type FinishResume,
  type ResumeContext,
} from "@/modules/editorial/workspace/lib/resume-workflow";
import type {
  EditorialReviseOptions,
  UseEditorialWorkflowResumeParams,
} from "./types";

export type { EditorialReviseOptions } from "./types";

/** The params as one object that only changes when one of its fields does. */
function useStableResumeDeps({
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
}: UseEditorialWorkflowResumeParams): UseEditorialWorkflowResumeParams {
  return useMemo(
    () => ({
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
    }),
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
}

/**
 * The final wait for the gate runs outside the try on purpose: it releases the
 * loading lock, and its "resumeFailed" is not shown as a resume error.
 */
export function useEditorialWorkflowResume(
  params: UseEditorialWorkflowResumeParams,
) {
  const deps = useStableResumeDeps(params);
  const resume = useCallback(
    async (
      action: string,
      feedback?: string,
      options?: EditorialReviseOptions,
    ): Promise<EditorialWorkflowState> => {
      deps.setLoading(true);
      deps.setError(null);
      const ctx: ResumeContext = {
        deps,
        actedOnPhase: deps.workflowStateRef.current?.current_phase,
      };
      markResumeRunning(ctx);
      let finish: FinishResume;
      try {
        finish = await sendResume(ctx, { action, feedback, options });
      } catch (err) {
        const message =
          err instanceof Error
            ? err.message
            : deps.translateError("resumeUnknown");
        deps.setError(message);
        await deps.refreshState();
        throw err;
      } finally {
        deps.setLoading(false);
      }
      return finish();
    },
    [deps],
  );

  return { resume };
}
