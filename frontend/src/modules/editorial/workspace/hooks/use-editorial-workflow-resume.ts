/** Resume/approve/revise actions for editorial workflow hook. */

import { useCallback } from "react";
import type { EditorialWorkflowState } from "@/modules/editorial/workspace/types-ai";
import {
  markResumeRunning,
  sendResume,
  type ResumeContext,
} from "@/modules/editorial/workspace/lib/resume-workflow";
import type {
  EditorialReviseOptions,
  UseEditorialWorkflowResumeParams,
} from "./types";

export type { EditorialReviseOptions } from "./types";

export function useEditorialWorkflowResume(
  deps: UseEditorialWorkflowResumeParams,
) {
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
      try {
        return await sendResume(ctx, { action, feedback, options });
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
    },
    [deps],
  );

  return { resume };
}
