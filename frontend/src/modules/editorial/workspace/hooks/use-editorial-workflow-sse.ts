/** SSE subscription and polling fallback for editorial workflow. */

import { useCallback, useEffect, useMemo, useRef, type RefObject } from "react";
import {
  EDITORIAL_WORKFLOW_POLL_BACKOFF_MS,
  EDITORIAL_WORKFLOW_TRANSPORT_MODE,
  type EditorialWorkflowTransportMode,
} from "@/constants/editorial-workflow";
import { WORKFLOW_PHASE_STATUS } from "@/constants/workflow";
import type { EditorialWorkflowState } from "@/modules/editorial/workspace/types-ai";
import {
  applyWorkflowEvent,
  openWorkflowStream,
  type StartStreamDeps,
  type StreamEventContext,
} from "@/modules/editorial/workspace/lib/workflow-stream-events";
import {
  appendUniquePhase,
  shouldPollWorkflowState,
} from "./use-editorial-workflow-utils";
import { useWorkflowStreamReconnect } from "./use-workflow-stream-reconnect";
import type {
  PollingControls,
  PollWhileFallbackDeps,
  StreamConnectionDeps,
  UseEditorialWorkflowSseParams,
  WorkflowStreamRefs,
} from "./types";

const LAST_BACKOFF_INDEX = EDITORIAL_WORKFLOW_POLL_BACKOFF_MS.length - 1;

function isPollingFallback(refs: WorkflowStreamRefs): boolean {
  return (
    refs.transportModeRef.current ===
    EDITORIAL_WORKFLOW_TRANSPORT_MODE.POLLING_FALLBACK
  );
}

/** The refs the stream, the poller and the reconnect logic share. */
function useStreamRefs(
  transportMode: EditorialWorkflowTransportMode,
  state: EditorialWorkflowState | null,
): WorkflowStreamRefs {
  const pollTimeoutRef = useRef<number | null>(null);
  const backoffIndexRef = useRef(0);
  const sourceRef = useRef<EventSource | null>(null);
  const connectRef = useRef<(() => void) | null>(null);
  const transportModeRef = useRef(transportMode);
  const workflowStateRef = useRef(state);
  const phaseStatusRef = useRef(state?.phase_status);
  // One stable object: effects and callbacks depend on it.
  const refs = useMemo<WorkflowStreamRefs>(
    () => ({
      pollTimeoutRef,
      backoffIndexRef,
      sourceRef,
      connectRef,
      transportModeRef,
      workflowStateRef,
      phaseStatusRef,
    }),
    [],
  );
  useEffect(() => {
    transportModeRef.current = transportMode;
    workflowStateRef.current = state;
    phaseStatusRef.current = state?.phase_status;
  }, [
    transportMode,
    state,
    transportModeRef,
    workflowStateRef,
    phaseStatusRef,
  ]);
  return refs;
}

/** Switch between live SSE, the polling fallback and "disconnected". */
function usePollingControls(
  { pollTimeoutRef, backoffIndexRef, transportModeRef }: WorkflowStreamRefs,
  setTransportMode: UseEditorialWorkflowSseParams["setTransportMode"],
): PollingControls {
  const clearPollTimeout = useCallback((): void => {
    if (pollTimeoutRef.current !== null) {
      window.clearTimeout(pollTimeoutRef.current);
      pollTimeoutRef.current = null;
    }
  }, [pollTimeoutRef]);
  const stopPollingFallback = useCallback((): void => {
    clearPollTimeout();
    backoffIndexRef.current = 0;
    setTransportMode(EDITORIAL_WORKFLOW_TRANSPORT_MODE.SSE);
  }, [clearPollTimeout, backoffIndexRef, setTransportMode]);
  const enterPollingFallback = useCallback((): void => {
    setTransportMode(EDITORIAL_WORKFLOW_TRANSPORT_MODE.POLLING_FALLBACK);
    backoffIndexRef.current = 0;
  }, [backoffIndexRef, setTransportMode]);
  const markDisconnected = useCallback((): void => {
    clearPollTimeout();
    transportModeRef.current = EDITORIAL_WORKFLOW_TRANSPORT_MODE.DISCONNECTED;
    setTransportMode(EDITORIAL_WORKFLOW_TRANSPORT_MODE.DISCONNECTED);
  }, [clearPollTimeout, transportModeRef, setTransportMode]);
  return {
    clearPollTimeout,
    stopPollingFallback,
    enterPollingFallback,
    markDisconnected,
  };
}

/** After a poll: back off further and re-arm, or stop on a failed read. */
function onPollAnswered(
  workflowState: EditorialWorkflowState | null,
  refs: WorkflowStreamRefs,
  next: { stopPollingFallback: () => void; reschedule: () => void },
): void {
  if (!workflowState) {
    // AE-0440: a poll answered after a disconnect must not hide it.
    if (isPollingFallback(refs)) {
      next.stopPollingFallback();
    }
    return;
  }
  refs.backoffIndexRef.current = Math.min(
    refs.backoffIndexRef.current + 1,
    LAST_BACKOFF_INDEX,
  );
  if (isPollingFallback(refs)) {
    next.reschedule();
  }
}

/** One poll after the backoff delay; it re-arms itself while polling. */
function useSchedulePoll(
  refs: WorkflowStreamRefs,
  { clearPollTimeout, stopPollingFallback }: PollingControls,
  refreshState: UseEditorialWorkflowSseParams["refreshState"],
): () => void {
  const scheduleRef = useRef<(() => void) | null>(null);
  const { phaseStatusRef, transportModeRef, backoffIndexRef, pollTimeoutRef } =
    refs;
  const schedulePollFallback = useCallback((): void => {
    clearPollTimeout();
    if (
      !shouldPollWorkflowState(
        phaseStatusRef.current,
        transportModeRef.current,
        EDITORIAL_WORKFLOW_TRANSPORT_MODE.POLLING_FALLBACK,
      )
    ) {
      return;
    }
    const delay =
      EDITORIAL_WORKFLOW_POLL_BACKOFF_MS[
        Math.min(backoffIndexRef.current, LAST_BACKOFF_INDEX)
      ];
    pollTimeoutRef.current = window.setTimeout(() => {
      void refreshState().then((workflowState) =>
        onPollAnswered(workflowState, refs, {
          stopPollingFallback,
          reschedule: () => scheduleRef.current?.(),
        }),
      );
    }, delay);
  }, [
    clearPollTimeout,
    refreshState,
    stopPollingFallback,
    refs,
    phaseStatusRef,
    transportModeRef,
    backoffIndexRef,
    pollTimeoutRef,
  ]);
  useEffect(() => {
    scheduleRef.current = schedulePollFallback;
  }, [schedulePollFallback]);
  return schedulePollFallback;
}

/** Close the live stream and forget how to reopen it. */
function closeStream(
  { sourceRef, connectRef }: WorkflowStreamRefs,
  cancel: () => void,
): void {
  cancel();
  connectRef.current = null;
  sourceRef.current?.close();
  sourceRef.current = null;
}

/** (Re)open the stream: events update the state, errors go to reconnect. */
function startStream(
  { sourceRef }: WorkflowStreamRefs,
  {
    eventContext,
    stopPollingFallback,
    handleStreamOpen,
    handleStreamError,
  }: StartStreamDeps,
): void {
  sourceRef.current?.close();
  sourceRef.current = openWorkflowStream(eventContext.projectId, {
    onEvent: (payload) => applyWorkflowEvent(payload, eventContext),
    onOpen: () => {
      stopPollingFallback();
      handleStreamOpen();
    },
    onError: (source) => {
      source.close();
      sourceRef.current = null;
      handleStreamError();
    },
  });
}

/** The stable inputs a stream event needs (re-created only when they change). */
function useStreamEventContext(
  {
    projectId,
    setState,
    setPhaseEvents,
    setError,
    refreshState,
  }: UseEditorialWorkflowSseParams,
  { workflowStateRef, phaseStatusRef }: WorkflowStreamRefs,
): StreamEventContext {
  return useMemo(
    () => ({
      projectId,
      setState,
      setPhaseEvents,
      setError,
      refreshState,
      workflowStateRef,
      phaseStatusRef,
    }),
    [
      projectId,
      setState,
      setPhaseEvents,
      setError,
      refreshState,
      workflowStateRef,
      phaseStatusRef,
    ],
  );
}

/** Open the stream while enabled; close it (and stop polling) on cleanup. */
function useStreamConnection({
  params,
  refs,
  controls,
  stream,
}: StreamConnectionDeps): void {
  const { sseEnabled } = params;
  const eventContext = useStreamEventContext(params, refs);
  const { clearPollTimeout, enterPollingFallback, stopPollingFallback } =
    controls;
  const { handleStreamError, handleStreamOpen, cancelReconnect } = stream;
  const { connectRef } = refs;
  useEffect(() => {
    const cancel = (): void => {
      clearPollTimeout();
      cancelReconnect();
    };
    if (!sseEnabled) {
      closeStream(refs, cancel);
      return;
    }
    if (typeof EventSource === "undefined") {
      enterPollingFallback();
      return;
    }
    const connectSse = (): void =>
      startStream(refs, {
        eventContext,
        stopPollingFallback,
        handleStreamOpen,
        handleStreamError,
      });
    connectRef.current = connectSse;
    connectSse();
    return () => closeStream(refs, cancel);
  }, [
    eventContext,
    sseEnabled,
    refs,
    clearPollTimeout,
    cancelReconnect,
    enterPollingFallback,
    handleStreamError,
    handleStreamOpen,
    stopPollingFallback,
    connectRef,
  ]);
}

/** While on the polling fallback, poll until a gate awaits the owner. */
function usePollWhileFallback({
  transportMode,
  phaseStatus,
  refs: { phaseStatusRef },
  clearPollTimeout,
  schedulePollFallback,
}: PollWhileFallbackDeps): void {
  useEffect(() => {
    if (transportMode !== EDITORIAL_WORKFLOW_TRANSPORT_MODE.POLLING_FALLBACK) {
      return;
    }
    if (phaseStatusRef.current === WORKFLOW_PHASE_STATUS.AWAITING_HUMAN) {
      clearPollTimeout();
      return;
    }
    schedulePollFallback();
  }, [
    transportMode,
    phaseStatus,
    clearPollTimeout,
    schedulePollFallback,
    phaseStatusRef,
  ]);
}

/** Adopt a state the reconnect probe fetched (refs + state + timeline). */
function useApplyProbedState(
  { workflowStateRef, phaseStatusRef }: WorkflowStreamRefs,
  { setState, setPhaseEvents }: UseEditorialWorkflowSseParams,
): (next: EditorialWorkflowState) => void {
  return useCallback(
    (next: EditorialWorkflowState): void => {
      workflowStateRef.current = next;
      phaseStatusRef.current = next.phase_status;
      setState(next);
      setPhaseEvents((prev) => appendUniquePhase(prev, next.current_phase));
    },
    [setPhaseEvents, setState, workflowStateRef, phaseStatusRef],
  );
}

export function useEditorialWorkflowSse(
  params: UseEditorialWorkflowSseParams,
): {
  enterPollingFallback: () => void;
  stopPollingFallback: () => void;
  reconnectLiveUpdates: () => void;
  transportModeRef: RefObject<EditorialWorkflowTransportMode>;
  workflowStateRef: RefObject<EditorialWorkflowState | null>;
} {
  const { projectId, state, transportMode, refreshState } = params;
  const refs = useStreamRefs(transportMode, state);
  const controls = usePollingControls(refs, params.setTransportMode);
  const { clearPollTimeout, stopPollingFallback, enterPollingFallback } =
    controls;
  const { connectRef, sourceRef, workflowStateRef } = refs;

  const applyProbedState = useApplyProbedState(refs, params);

  const { handleStreamError, handleStreamOpen, reconnectNow, cancelReconnect } =
    useWorkflowStreamReconnect({
      projectId,
      connectRef,
      sourceRef,
      applyProbedState,
      refreshState,
      enterPollingFallback,
      markDisconnected: controls.markDisconnected,
    });
  const schedulePollFallback = useSchedulePoll(refs, controls, refreshState);

  useStreamConnection({
    params,
    refs,
    controls,
    stream: { handleStreamError, handleStreamOpen, cancelReconnect },
  });
  usePollWhileFallback({
    transportMode,
    phaseStatus: state?.phase_status,
    refs,
    clearPollTimeout,
    schedulePollFallback,
  });

  return {
    enterPollingFallback,
    stopPollingFallback,
    reconnectLiveUpdates: reconnectNow,
    transportModeRef: refs.transportModeRef,
    workflowStateRef,
  };
}
