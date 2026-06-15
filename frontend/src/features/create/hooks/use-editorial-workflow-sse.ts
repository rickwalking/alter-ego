/** SSE subscription and polling fallback for editorial workflow. */

import {
  useCallback,
  useEffect,
  useRef,
  type Dispatch,
  type RefObject,
  type SetStateAction,
} from "react";
import { API_ENDPOINTS } from "@/constants/api";
import {
  EDITORIAL_WORKFLOW_POLL_BACKOFF_MS,
  EDITORIAL_WORKFLOW_SSE_EVENTS,
  EDITORIAL_WORKFLOW_TRANSPORT_MODE,
  type EditorialWorkflowTransportMode,
} from "@/constants/editorial-workflow";
import { WORKFLOW_PHASE_STATUS } from "@/constants/workflow";
import type { EditorialWorkflowState } from "@/features/blog/types-ai";
import {
  appendUniquePhase,
  mergeWorkflowState,
  normalizeProgressPayload,
  parseWorkflowEvent,
  resolveWorkflowEventPayload,
  shouldPollWorkflowState,
  type WorkflowEventPayload,
} from "./use-editorial-workflow-utils";

interface UseEditorialWorkflowSseParams {
  projectId: string;
  sseEnabled: boolean;
  state: EditorialWorkflowState | null;
  transportMode: EditorialWorkflowTransportMode;
  setState: Dispatch<SetStateAction<EditorialWorkflowState | null>>;
  setPhaseEvents: Dispatch<SetStateAction<string[]>>;
  setTransportMode: Dispatch<SetStateAction<EditorialWorkflowTransportMode>>;
  setError: Dispatch<SetStateAction<string | null>>;
  refreshState: () => Promise<EditorialWorkflowState | null>;
}

export function useEditorialWorkflowSse({
  projectId,
  sseEnabled,
  state,
  transportMode,
  setState,
  setPhaseEvents,
  setTransportMode,
  setError,
  refreshState,
}: UseEditorialWorkflowSseParams): {
  enterPollingFallback: () => void;
  stopPollingFallback: () => void;
  transportModeRef: RefObject<EditorialWorkflowTransportMode>;
  workflowStateRef: RefObject<EditorialWorkflowState | null>;
} {
  const pollTimeoutRef = useRef<number | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const backoffIndexRef = useRef(0);
  const sourceRef = useRef<EventSource | null>(null);
  const transportModeRef = useRef(transportMode);
  const workflowStateRef = useRef(state);
  const phaseStatusRef = useRef(state?.phase_status);

  useEffect(() => {
    transportModeRef.current = transportMode;
    workflowStateRef.current = state;
    phaseStatusRef.current = state?.phase_status;
  }, [transportMode, state]);

  const clearPollTimeout = useCallback((): void => {
    if (pollTimeoutRef.current !== null) {
      window.clearTimeout(pollTimeoutRef.current);
      pollTimeoutRef.current = null;
    }
  }, []);

  const clearReconnectTimeout = useCallback((): void => {
    if (reconnectTimeoutRef.current !== null) {
      window.clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
  }, []);

  const stopPollingFallback = useCallback((): void => {
    clearPollTimeout();
    backoffIndexRef.current = 0;
    setTransportMode(EDITORIAL_WORKFLOW_TRANSPORT_MODE.SSE);
  }, [clearPollTimeout, setTransportMode]);

  const enterPollingFallback = useCallback((): void => {
    setTransportMode(EDITORIAL_WORKFLOW_TRANSPORT_MODE.POLLING_FALLBACK);
    backoffIndexRef.current = 0;
  }, [setTransportMode]);

  const schedulePollFallbackRef = useRef<(() => void) | null>(null);

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

    const backoffIndex = Math.min(
      backoffIndexRef.current,
      EDITORIAL_WORKFLOW_POLL_BACKOFF_MS.length - 1,
    );
    const delay = EDITORIAL_WORKFLOW_POLL_BACKOFF_MS[backoffIndex];

    pollTimeoutRef.current = window.setTimeout(() => {
      void refreshState().then((workflowState) => {
        if (!workflowState) {
          stopPollingFallback();
          return;
        }
        backoffIndexRef.current = Math.min(
          backoffIndexRef.current + 1,
          EDITORIAL_WORKFLOW_POLL_BACKOFF_MS.length - 1,
        );
        if (
          transportModeRef.current ===
          EDITORIAL_WORKFLOW_TRANSPORT_MODE.POLLING_FALLBACK
        ) {
          schedulePollFallbackRef.current?.();
        }
      });
    }, delay);
  }, [clearPollTimeout, refreshState, stopPollingFallback]);

  useEffect(() => {
    schedulePollFallbackRef.current = schedulePollFallback;
  }, [schedulePollFallback]);

  useEffect(() => {
    if (!sseEnabled) {
      clearPollTimeout();
      clearReconnectTimeout();
      sourceRef.current?.close();
      sourceRef.current = null;
      return;
    }

    if (typeof EventSource === "undefined") {
      enterPollingFallback();
      return;
    }

    const applyEventPayload = (payload: WorkflowEventPayload): void => {
      if (payload.event === EDITORIAL_WORKFLOW_SSE_EVENTS.ERROR) {
        if (payload.recoverable) {
          return;
        }
        if (typeof payload.message === "string" && payload.message.trim()) {
          setError(payload.message);
        }
        return;
      }

      const resolved = resolveWorkflowEventPayload(payload);
      const phase = resolved.phase ?? resolved.current_phase;
      if (phase) {
        setPhaseEvents((prev) => appendUniquePhase(prev, phase));
      }
      const hasProgressUpdate = Boolean(normalizeProgressPayload(resolved));
      if (
        resolved.phase ||
        resolved.current_phase ||
        resolved.phase_status ||
        hasProgressUpdate ||
        resolved.event === EDITORIAL_WORKFLOW_SSE_EVENTS.REVIEW_REQUIRED ||
        resolved.event === EDITORIAL_WORKFLOW_SSE_EVENTS.ARTIFACT
      ) {
        const merged = mergeWorkflowState(
          projectId,
          workflowStateRef.current,
          resolved,
        );
        workflowStateRef.current = merged;
        phaseStatusRef.current = merged.phase_status;
        setState(merged);
      }
    };

    const handleSseMessage = (event: MessageEvent<string>): void => {
      const payload = parseWorkflowEvent(event.data);
      if (!payload) {
        return;
      }
      applyEventPayload(payload);
    };

    const connectSse = (): void => {
      sourceRef.current?.close();
      clearReconnectTimeout();

      const source = new EventSource(
        API_ENDPOINTS.CAROUSEL_WORKFLOW_STREAM(projectId),
        { withCredentials: true },
      );
      sourceRef.current = source;

      source.addEventListener(
        EDITORIAL_WORKFLOW_SSE_EVENTS.PHASE_CHANGED,
        handleSseMessage,
      );
      source.addEventListener(
        EDITORIAL_WORKFLOW_SSE_EVENTS.PROGRESS,
        handleSseMessage,
      );
      source.addEventListener(
        EDITORIAL_WORKFLOW_SSE_EVENTS.REVIEW_REQUIRED,
        handleSseMessage,
      );
      source.addEventListener(
        EDITORIAL_WORKFLOW_SSE_EVENTS.ERROR,
        handleSseMessage,
      );
      source.addEventListener(
        EDITORIAL_WORKFLOW_SSE_EVENTS.ARTIFACT,
        handleSseMessage,
      );
      source.onmessage = handleSseMessage;

      source.onopen = () => {
        stopPollingFallback();
      };

      source.onerror = () => {
        source.close();
        sourceRef.current = null;
        enterPollingFallback();
        reconnectTimeoutRef.current = window.setTimeout(() => {
          connectSse();
        }, EDITORIAL_WORKFLOW_POLL_BACKOFF_MS[0]);
      };
    };

    connectSse();

    return () => {
      clearPollTimeout();
      clearReconnectTimeout();
      sourceRef.current?.close();
      sourceRef.current = null;
    };
  }, [
    projectId,
    sseEnabled,
    clearPollTimeout,
    clearReconnectTimeout,
    enterPollingFallback,
    setError,
    setPhaseEvents,
    setState,
    stopPollingFallback,
  ]);

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
    state?.phase_status,
    clearPollTimeout,
    schedulePollFallback,
  ]);

  return {
    enterPollingFallback,
    stopPollingFallback,
    transportModeRef,
    workflowStateRef,
  };
}
