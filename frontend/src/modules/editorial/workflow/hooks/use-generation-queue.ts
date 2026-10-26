"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { z } from "zod";
import {
  QUEUE_ACTION,
  QUEUE_API,
  REPROCESS_REFUSAL_CODES,
  WORKFLOW_API,
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
  GenerationQueueActionResult,
  GenerationQueueActionState,
  GenerationQueueLoadResult,
  GenerationQueueMaintenanceDeps,
  GenerationQueueMaintenanceState,
  GenerationQueueReprocessTarget,
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
type PostOutcome = GenerationQueueActionResult["outcome"];
const conflictSchema = z.object({ detail: z.string() });
const CONFLICT = 409;
const FORBIDDEN = 403;
const NO_PENDING: ReadonlySet<string> = new Set<string>();

/** Polls on the board interval and focus until unmount or forbidden access. */
function usePolling(load: () => Promise<void>, stopped: boolean): void {
  useEffect(() => {
    if (stopped) return;
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
  }, [load, stopped]);
}

function actionUrl(
  action: QueueAction,
  id: string,
  reprocess: GenerationQueueReprocessTarget | undefined,
): string {
  if (action === QUEUE_ACTION.REPROCESS && reprocess?.projectId !== undefined) {
    return WORKFLOW_API.CAROUSEL_REPROCESS(reprocess.projectId);
  }
  return ACTION_URL[action](id);
}

function actionBody(
  action: QueueAction,
  reprocess: GenerationQueueReprocessTarget | undefined,
): string {
  if (action !== QUEUE_ACTION.REPROCESS) return NO_BODY;
  if (reprocess?.projectId !== undefined) {
    return JSON.stringify({
      expected_version: reprocess.expectedVersion,
      run_id: null,
    });
  }
  if (reprocess?.expectedVersion === undefined) return NO_BODY;
  return JSON.stringify({ expected_version: reprocess.expectedVersion });
}

function actionResult(outcome: PostOutcome): GenerationQueueActionResult {
  return { outcome, refusalCode: null };
}

function reprocessConflict(body: unknown): GenerationQueueActionResult {
  const parsed = conflictSchema.safeParse(body);
  const refusalCode =
    parsed.success && REPROCESS_REFUSAL_CODES.has(parsed.data.detail)
      ? parsed.data.detail
      : null;
  return { outcome: POST_OUTCOME.NOT_ALLOWED, refusalCode };
}

/** Posts one panel action and retains only recognized reprocess refusal codes. */
async function postAction(
  action: QueueAction,
  id: string,
  reprocess?: GenerationQueueReprocessTarget,
): Promise<GenerationQueueActionResult> {
  try {
    const response = await authenticatedFetch(
      actionUrl(action, id, reprocess),
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: actionBody(action, reprocess),
      },
    );
    if (response.status === CONFLICT) {
      if (action === QUEUE_ACTION.REPROCESS) {
        const body: unknown = await response.json().catch((): null => null);
        return reprocessConflict(body);
      }
      const body = conflictSchema.safeParse(await response.json());
      return actionResult(
        body.success && body.data.detail === NOT_ALLOWED
          ? POST_OUTCOME.NOT_ALLOWED
          : POST_OUTCOME.DONE,
      );
    }
    if (!response.ok) return actionResult(POST_OUTCOME.FAILED);
    queueActionResponseSchema.parse(await response.json());
    return actionResult(POST_OUTCOME.DONE);
  } catch {
    return actionResult(POST_OUTCOME.FAILED);
  }
}

function actionErrorMessage(
  result: GenerationQueueActionResult,
  translate: (key: string) => string,
  translateReprocess: (key: string) => string,
): string | null {
  if (result.outcome === POST_OUTCOME.FAILED) {
    return translate("actionFailed");
  }
  if (result.outcome !== POST_OUTCOME.NOT_ALLOWED) return null;
  if (result.refusalCode !== null) {
    return translateReprocess(`refusals.${result.refusalCode}`);
  }
  return translate("notAllowed");
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

function useQueueActions(
  load: () => Promise<void>,
  translate: (key: string) => string,
  translateReprocess: (key: string) => string,
): GenerationQueueActionState {
  const [pending, setPending] = useState<ReadonlySet<string>>(NO_PENDING);
  const [actionError, setActionError] = useState<string | null>(null);
  const pendingRef = useRef<ReadonlySet<string>>(NO_PENDING);
  const setRowPending = useCallback((id: string, isPending: boolean): void => {
    const next = new Set(pendingRef.current);
    if (isPending) next.add(id);
    if (!isPending) next.delete(id);
    pendingRef.current = next;
    setPending(next);
  }, []);
  const act = useCallback(
    async (
      action: QueueAction,
      id: string,
      reprocess?: GenerationQueueReprocessTarget,
    ): Promise<void> => {
      if (pendingRef.current.has(id)) return;
      setRowPending(id, true);
      setActionError(null);
      try {
        const result = await postAction(action, id, reprocess);
        setActionError(
          actionErrorMessage(result, translate, translateReprocess),
        );
      } finally {
        setRowPending(id, false);
      }
      await load();
    },
    [load, setRowPending, translate, translateReprocess],
  );
  return { pending, actionError, act };
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
  const tReprocess = useTranslations("workflow.reprocess");
  const [board, setBoard] = useState<QueueBoard | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pollingStopped, setPollingStopped] = useState(false);
  const latestRequestRef = useRef(0);
  const forbiddenRef = useRef(false);

  const load = useCallback(async (): Promise<void> => {
    if (forbiddenRef.current) return;
    const requestId = latestRequestRef.current + 1;
    latestRequestRef.current = requestId;
    const loaded = await loadBoard(t("loadFailed"));
    if (loaded.forbidden) {
      forbiddenRef.current = true;
      latestRequestRef.current += 1;
      setPollingStopped(true);
      setBoard(null);
      setError(null);
      return;
    }
    if (requestId !== latestRequestRef.current) return;
    setError(loaded.error);
    if (loaded.error === null) setBoard(loaded.board);
  }, [t]);

  const actions = useQueueActions(load, t, tReprocess);
  const maintenance = useQueueMaintenance(load, t);
  usePolling(load, pollingStopped);
  return { board, error, ...actions, ...maintenance };
}

/** The board or load error, with forbidden access latched by the caller. */
async function loadBoard(failed: string): Promise<GenerationQueueLoadResult> {
  try {
    const response = await authenticatedFetch(QUEUE_API.BOARD);
    if (response.status === FORBIDDEN) {
      return { board: null, error: null, forbidden: true };
    }
    if (!response.ok) {
      return { board: null, error: failed, forbidden: false };
    }
    return {
      board: queueBoardResponseSchema.parse(await response.json()),
      error: null,
      forbidden: false,
    };
  } catch {
    return { board: null, error: failed, forbidden: false };
  }
}
