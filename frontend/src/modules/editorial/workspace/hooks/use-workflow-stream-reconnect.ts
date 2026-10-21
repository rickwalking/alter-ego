/**
 * AE-0440: recovery of the editorial workflow stream after an error.
 *
 * The old onerror reconnected after the first backoff delay forever and could
 * not tell an expired session from a dropped connection (prod, 2026-10-20: a
 * 401 every 6 s for 5+ hours while the page kept stale state). Now every stream
 * error is followed by an auth probe (``probeWorkflowStream``): a 401/403 stops
 * here (the api-client already redirected), a 404 disconnects, anything else
 * applies the refetched state and reconnects with the whole backoff array,
 * capped at ``EDITORIAL_WORKFLOW_SSE_MAX_RECONNECT_ATTEMPTS``. Returning to the
 * tab probes again and revives a stream that gave up.
 */

import { useCallback, useEffect, useRef } from "react";
import {
  EDITORIAL_WORKFLOW_POLL_BACKOFF_MS,
  EDITORIAL_WORKFLOW_SSE_MAX_RECONNECT_ATTEMPTS,
  WORKFLOW_STREAM_PROBE_OUTCOME,
} from "@/constants/editorial-workflow";
import { probeWorkflowStream } from "./workflow-stream-probe";
import type {
  UseWorkflowStreamReconnectParams,
  WorkflowStreamProbeResult,
  WorkflowStreamReconnectApi,
} from "./types";

const DOCUMENT_VISIBILITY_EVENT = "visibilitychange";
const DOCUMENT_VISIBLE = "visible";

function reconnectDelay(attempt: number): number {
  const backoff = EDITORIAL_WORKFLOW_POLL_BACKOFF_MS;
  return backoff[Math.min(attempt, backoff.length - 1)] ?? backoff[0];
}

export function useWorkflowStreamReconnect({
  projectId,
  connectRef,
  sourceRef,
  applyProbedState,
  refreshState,
  enterPollingFallback,
  markDisconnected,
}: UseWorkflowStreamReconnectParams): WorkflowStreamReconnectApi {
  const attemptsRef = useRef(0);
  const timeoutRef = useRef<number | null>(null);
  // True between a stream error and the next open: that open is a reconnect.
  const failedRef = useRef(false);
  // Bumped on cancel so a probe answered after unmount / project change is dropped.
  const generationRef = useRef(0);

  const clearTimer = useCallback((): void => {
    if (timeoutRef.current !== null) {
      window.clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
  }, []);

  const cancelReconnect = useCallback((): void => {
    clearTimer();
    attemptsRef.current = 0;
    failedRef.current = false;
    generationRef.current += 1;
  }, [clearTimer]);

  const scheduleReconnect = useCallback((): void => {
    if (attemptsRef.current >= EDITORIAL_WORKFLOW_SSE_MAX_RECONNECT_ATTEMPTS) {
      markDisconnected();
      return;
    }
    const delay = reconnectDelay(attemptsRef.current);
    attemptsRef.current += 1;
    timeoutRef.current = window.setTimeout(() => {
      timeoutRef.current = null;
      connectRef.current?.();
    }, delay);
  }, [connectRef, markDisconnected]);

  /** Apply the probe verdict; true when the stream may be reopened. */
  const applyProbe = useCallback(
    (result: WorkflowStreamProbeResult): boolean => {
      if (result.outcome === WORKFLOW_STREAM_PROBE_OUTCOME.OK) {
        if (result.state) {
          applyProbedState(result.state);
        }
        return true;
      }
      if (result.outcome === WORKFLOW_STREAM_PROBE_OUTCOME.TRANSIENT) {
        return true;
      }
      // AUTH_FAILED (api-client redirected to the session-expired login) or GONE.
      markDisconnected();
      return false;
    },
    [applyProbedState, markDisconnected],
  );

  const probeThen = useCallback(
    (onReopenable: () => void): void => {
      const generation = generationRef.current;
      void probeWorkflowStream(projectId).then((result) => {
        if (generation !== generationRef.current) {
          return;
        }
        if (applyProbe(result)) {
          onReopenable();
        }
      });
    },
    [applyProbe, projectId],
  );

  const handleStreamError = useCallback((): void => {
    clearTimer();
    failedRef.current = true;
    enterPollingFallback();
    probeThen(scheduleReconnect);
  }, [clearTimer, enterPollingFallback, probeThen, scheduleReconnect]);

  const handleStreamOpen = useCallback((): void => {
    const isReconnect = failedRef.current;
    attemptsRef.current = 0;
    failedRef.current = false;
    if (isReconnect) {
      void refreshState();
    }
  }, [refreshState]);

  const reconnectNow = useCallback((): void => {
    clearTimer();
    attemptsRef.current = 0;
    connectRef.current?.();
  }, [clearTimer, connectRef]);

  useEffect(() => {
    const onVisibilityChange = (): void => {
      if (
        document.visibilityState !== DOCUMENT_VISIBLE ||
        !connectRef.current
      ) {
        return;
      }
      if (sourceRef.current) {
        void refreshState();
        return;
      }
      probeThen(reconnectNow);
    };
    document.addEventListener(DOCUMENT_VISIBILITY_EVENT, onVisibilityChange);
    return () => {
      document.removeEventListener(
        DOCUMENT_VISIBILITY_EVENT,
        onVisibilityChange,
      );
    };
  }, [connectRef, probeThen, reconnectNow, refreshState, sourceRef]);

  return { handleStreamError, handleStreamOpen, reconnectNow, cancelReconnect };
}
