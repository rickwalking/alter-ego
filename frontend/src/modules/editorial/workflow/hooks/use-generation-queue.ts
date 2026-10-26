"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { z } from "zod";
import {
  QUEUE_ACTION,
  QUEUE_API,
  WORKFLOW_BOARD_POLL_INTERVAL_MS,
  type QueueAction,
} from "@/constants/workflow";
import { authenticatedFetch } from "@/lib/authenticated-fetch";
import {
  queueActionResponseSchema,
  queueBoardResponseSchema,
  queueMaintenanceResponseSchema,
  type QueueBoard,
} from "@/schemas/generation-queue";
import type {
  GenerationQueueMaintenanceDeps,
  GenerationQueueMaintenanceState,
  GenerationQueueState,
} from "./types";

const ACTION_URL: Record<QueueAction, (id: string) => string> = {
  [QUEUE_ACTION.RETRY]: QUEUE_API.RETRY,
  [QUEUE_ACTION.DISCARD]: QUEUE_API.DISCARD,
  [QUEUE_ACTION.CANCEL]: QUEUE_API.CANCEL,
  [QUEUE_ACTION.REPROCESS]: QUEUE_API.REPROCESS,
  [QUEUE_ACTION.GENERATE_NOW]: QUEUE_API.GENERATE_NOW,
};

const NO_BODY = "{}";
const NOT_ALLOWED = "not_allowed";
const POST_OUTCOME = {
  DONE: "done",
  NOT_ALLOWED: "notAllowed",
  FORBIDDEN: "forbidden",
  FAILED: "failed",
} as const;
type PostOutcome = (typeof POST_OUTCOME)[keyof typeof POST_OUTCOME];
const conflictSchema = z.object({ detail: z.string() });
const CONFLICT = 409;
const FORBIDDEN = 403;

/** Polls `load` on the board's interval and on window focus until unmount. */
function usePolling(load: () => Promise<void>): void {
  useEffect(() => {
    void load();
    const intervalId = window.setInterval(() => {
      void load();
    }, WORKFLOW_BOARD_POLL_INTERVAL_MS);
    const handleFocus = (): void => {
      void load();
    };
    window.addEventListener("focus", handleFocus);
    return () => {
      window.clearInterval(intervalId);
      window.removeEventListener("focus", handleFocus);
    };
  }, [load]);
}

/**
 * Posts one panel button: `done` when it went through or someone already resolved
 * it (409 `already_resolved`), `notAllowed` when the run can no longer take this
 * button (409 `not_allowed`), `failed` otherwise.
 */
async function postAction(
  action: QueueAction,
  id: string,
): Promise<PostOutcome> {
  try {
    const response = await authenticatedFetch(ACTION_URL[action](id), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: NO_BODY,
    });
    if (response.status === CONFLICT) {
      if (action === QUEUE_ACTION.REPROCESS) return POST_OUTCOME.NOT_ALLOWED;
      const body = conflictSchema.safeParse(await response.json());
      return body.success && body.data.detail === NOT_ALLOWED
        ? POST_OUTCOME.NOT_ALLOWED
        : POST_OUTCOME.DONE;
    }
    if (!response.ok) return POST_OUTCOME.FAILED;
    queueActionResponseSchema.parse(await response.json());
    return POST_OUTCOME.DONE;
  } catch {
    return POST_OUTCOME.FAILED;
  }
}

async function postMaintenance(): Promise<PostOutcome> {
  try {
    const response = await authenticatedFetch(QUEUE_API.PROCESS, {
      method: "POST",
    });
    if (response.status === FORBIDDEN) return POST_OUTCOME.FORBIDDEN;
    if (!response.ok) return POST_OUTCOME.FAILED;
    queueMaintenanceResponseSchema.parse(await response.json());
    return POST_OUTCOME.DONE;
  } catch {
    return POST_OUTCOME.FAILED;
  }
}

async function runQueueMaintenance(
  deps: GenerationQueueMaintenanceDeps,
): Promise<void> {
  if (deps.processInFlightRef.current) return;
  deps.processInFlightRef.current = true;
  deps.setProcessPending(true);
  deps.setProcessError(null);
  try {
    const outcome = await postMaintenance();
    if (outcome === POST_OUTCOME.FAILED) {
      deps.setProcessError(deps.translate("processFailed"));
      return;
    }
    if (outcome === POST_OUTCOME.FORBIDDEN) {
      deps.setProcessError(deps.translate("processForbidden"));
      return;
    }
    await deps.load();
  } finally {
    deps.processInFlightRef.current = false;
    deps.setProcessPending(false);
  }
}

function useQueueMaintenance(
  load: () => Promise<void>,
  translate: (key: string) => string,
): GenerationQueueMaintenanceState {
  const [processPending, setProcessPending] = useState(false);
  const [processError, setProcessError] = useState<string | null>(null);
  const processInFlightRef = useRef(false);
  const processQueue = useCallback(
    (): Promise<void> =>
      runQueueMaintenance({
        load,
        translate,
        processInFlightRef,
        setProcessPending,
        setProcessError,
      }),
    [load, translate],
  );
  return { processPending, processError, processQueue };
}

/**
 * Loads the generation queue panel and refreshes it on the board's poll and on
 * window focus (only the newest answer may update it; a failed refresh keeps the
 * last panel). The panel is admin-only:
 * a 403 hides it without an error. `act` posts one button and reloads the panel;
 * an "already resolved" answer (409) reloads without an error (Telegram or another
 * tab got there first).
 */
export function useGenerationQueue(): GenerationQueueState {
  const t = useTranslations("workflow.queue");
  const [board, setBoard] = useState<QueueBoard | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const latestRequestRef = useRef(0);

  const load = useCallback(async (): Promise<void> => {
    const requestId = latestRequestRef.current + 1;
    latestRequestRef.current = requestId;
    const loaded = await loadBoard(t("loadFailed"));
    if (requestId !== latestRequestRef.current) return;
    setError(loaded.error);
    if (loaded.error === null) setBoard(loaded.board);
  }, [t]);

  const act = useCallback(
    async (action: QueueAction, id: string): Promise<void> => {
      setPending(id);
      setActionError(null);
      const outcome = await postAction(action, id);
      if (outcome === POST_OUTCOME.FAILED) setActionError(t("actionFailed"));
      if (outcome === POST_OUTCOME.NOT_ALLOWED) setActionError(t("notAllowed"));
      setPending(null);
      await load();
    },
    [load, t],
  );

  const maintenance = useQueueMaintenance(load, t);
  usePolling(load);
  return { board, error, pending, actionError, act, ...maintenance };
}

/** The board or the load error; a 403 (not an admin) is neither. */
async function loadBoard(
  failed: string,
): Promise<{ board: QueueBoard | null; error: string | null }> {
  try {
    const response = await authenticatedFetch(QUEUE_API.BOARD);
    if (response.status === FORBIDDEN) return { board: null, error: null };
    if (!response.ok) return { board: null, error: failed };
    return {
      board: queueBoardResponseSchema.parse(await response.json()),
      error: null,
    };
  } catch {
    return { board: null, error: failed };
  }
}
