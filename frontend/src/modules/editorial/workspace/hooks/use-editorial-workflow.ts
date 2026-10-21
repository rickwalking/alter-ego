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
  StartWorkflowDeps,
  WorkflowCore,
  StartWorkflowInput,
  UseEditorialWorkflowOptions,
} from "./types";

export type { EditorialReviseOptions };

/**
 * An edits-only revise (content manual fixes, design recovery)
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

/** GET the workflow state; null when it does not exist or the read failed. */
async function fetchWorkflowState(
  projectId: string,
): Promise<EditorialWorkflowState | null> {
  try {
    const response = await authenticatedFetch(
      API_ENDPOINTS.CAROUSEL_WORKFLOW_STATE(projectId),
    );
    if (response.status === HTTP_STATUS.NOT_FOUND || !response.ok) {
      return null;
    }
    return (await response.json()) as EditorialWorkflowState;
  } catch {
    return null;
  }
}

/** Store a server state and record its phase in the phase timeline. */
function adoptState(
  workflowState: EditorialWorkflowState,
  {
    setState,
    setPhaseEvents,
  }: Pick<StartWorkflowDeps, "setState" | "setPhaseEvents">,
): void {
  setState(workflowState);
  if (workflowState.current_phase) {
    setPhaseEvents((prev) =>
      appendUniquePhase(prev, workflowState.current_phase),
    );
  }
}

async function postWorkflowStart(
  projectId: string,
  input: StartWorkflowInput,
  failure: string,
): Promise<EditorialWorkflowState> {
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
    throw new Error(await readApiError(response, failure));
  }
  return (await response.json()) as EditorialWorkflowState;
}

/** Start the workflow; on failure show the error and re-read the state. */
function useStartWorkflow(
  deps: StartWorkflowDeps,
): (input: StartWorkflowInput) => Promise<EditorialWorkflowState> {
  const { projectId, translateError: t, workflowStateRef, refreshState } = deps;
  const { setState, setPhaseEvents, setLoading, setError } = deps;
  return useCallback(
    async (input: StartWorkflowInput): Promise<EditorialWorkflowState> => {
      setLoading(true);
      setError(null);
      try {
        const workflowState = await postWorkflowStart(
          projectId,
          input,
          t("startFailed"),
        );
        adoptState(workflowState, { setState, setPhaseEvents });
        workflowStateRef.current = workflowState;
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
    [
      projectId,
      refreshState,
      t,
      workflowStateRef,
      setState,
      setPhaseEvents,
      setLoading,
      setError,
    ],
  );
}

type ResumeFn = ReturnType<typeof useEditorialWorkflowResume>["resume"];

/** Approve / revise, remembering which action started the run. */
function reviewActions(
  resume: ResumeFn,
  state: EditorialWorkflowState | null,
  setLastResume: (value: RecordedResume) => void,
) {
  const phase = state?.current_phase ?? "";
  return {
    approve: (reviseOptions?: EditorialReviseOptions) => {
      setLastResume({ action: EDITORIAL_REVIEW_ACTIONS.APPROVE, phase });
      return resume(EDITORIAL_REVIEW_ACTIONS.APPROVE, undefined, reviseOptions);
    },
    revise: (
      feedback: string,
      reviseOptions?: EditorialReviseOptions,
    ): Promise<EditorialWorkflowState | null> => {
      setLastResume({ action: EDITORIAL_REVIEW_ACTIONS.REVISE, phase });
      const pending = resume(
        EDITORIAL_REVIEW_ACTIONS.REVISE,
        feedback,
        reviseOptions,
      );
      return isEditsOnlyRevise(feedback, reviseOptions)
        ? pending.catch(() => null)
        : pending;
    },
  };
}

/** The hook's own state plus the GET that refreshes it. */
function useWorkflowCore(projectId: string): WorkflowCore {
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
      const workflowState = await fetchWorkflowState(projectId);
      if (workflowState) {
        adoptState(workflowState, { setState, setPhaseEvents });
      }
      return workflowState;
    }, [projectId]);
  return {
    state,
    setState,
    phaseEvents,
    setPhaseEvents,
    loading,
    setLoading,
    error,
    setError,
    transportMode,
    setTransportMode,
    refreshState,
  };
}

/**
 * A project that never started its workflow has no state
 * (GET answers 404); callers that know this skip the request.
 */
function useInitialRefresh(
  initialFetch: boolean,
  refreshState: () => Promise<unknown>,
): void {
  useEffect(() => {
    if (!initialFetch) {
      return;
    }
    void refreshState();
  }, [initialFetch, refreshState]);
}

/**
 * Records which review action started the current run, and on which phase, so
 * the running banner names the phase that is really running.
 */
export function useEditorialWorkflow(
  projectId: string,
  options?: UseEditorialWorkflowOptions,
) {
  const t = useTranslations("editorialWorkflow.errors");
  const core = useWorkflowCore(projectId);
  const { state, refreshState } = core;
  const [lastResume, setLastResume] = useState<RecordedResume | null>(null);
  const sse = useEditorialWorkflowSse({
    ...core,
    projectId,
    sseEnabled: Boolean(state?.current_phase),
  });
  useInitialRefresh(options?.initialFetch ?? true, refreshState);
  const { workflowStateRef } = sse;
  const { resume } = useEditorialWorkflowResume({
    ...core,
    ...sse,
    projectId,
    lockVersion: state?.lock_version,
    translateError: t,
  });
  const start = useStartWorkflow({
    ...core,
    projectId,
    translateError: t,
    workflowStateRef,
  });

  return {
    state,
    phaseEvents: core.phaseEvents,
    loading: core.loading,
    error: core.error,
    transportMode: core.transportMode,
    reconnectLiveUpdates: sse.reconnectLiveUpdates,
    start,
    resume,
    refreshState,
    ...reviewActions(resume, state, setLastResume),
    runningAction: resolveRunningAction(state, lastResume),
    awaitingHumanReview:
      state?.phase_status === WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
    hasActiveWorkflow: Boolean(state?.current_phase),
  };
}
