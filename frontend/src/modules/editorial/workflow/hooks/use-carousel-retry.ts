"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { HTTP_STATUS } from "@/constants/api";
import {
  RETRY_REFUSAL,
  RETRY_REFUSAL_CODES,
  RETRY_TEMPORARY_REFUSALS,
  RETRY_TOAST_VARIANT,
  WORKFLOW_BOARD_POLL_INTERVAL_MS,
  WORKFLOW_PHASE_STATUS,
} from "@/constants/workflow";
import { ApiError } from "@/lib/api-client";
import type { CarouselRetryCapability } from "@/schemas/carousel-retry";
import {
  fetchCarouselRetryCapability,
  postCarouselRetry,
} from "./carousel-retry-requests";
import { carouselReprocessKeys } from "./use-carousel-reprocess";
import type {
  CarouselRetryRefusal,
  CarouselRetryRunDeps,
  CarouselRetryState,
  CarouselRetryToast,
  CarouselRetryWorkflowState,
  ShowCarouselRetryToast,
  UseCarouselRetryOptions,
} from "./types";

const MIN_LOCK_VERSION = 1;
const RETRY_QUERY_KEY = "carousel-retry";
const FINISHED_OK_KEY = "finishedOk";
const FINISHED_FAILED_KEY = "finishedFailed";

/** How a running retry ended, by the phase status it stopped at. */
const OUTCOME_BY_STATUS: Readonly<
  Record<string, { key: string; variant: CarouselRetryToast["variant"] }>
> = {
  [WORKFLOW_PHASE_STATUS.AWAITING_HUMAN]: {
    key: FINISHED_OK_KEY,
    variant: RETRY_TOAST_VARIANT.SUCCESS,
  },
  [WORKFLOW_PHASE_STATUS.FAILED]: {
    key: FINISHED_FAILED_KEY,
    variant: RETRY_TOAST_VARIANT.ERROR,
  },
  [WORKFLOW_PHASE_STATUS.REJECTED]: {
    key: FINISHED_FAILED_KEY,
    variant: RETRY_TOAST_VARIANT.ERROR,
  },
};

function workflowStateKey(state: CarouselRetryWorkflowState | null): string {
  return [state?.current_phase, state?.phase_status, state?.lock_version].join(
    "/",
  );
}

function usableVersion(
  capability: CarouselRetryCapability | null,
  state: CarouselRetryWorkflowState | null,
): number | null {
  const version = capability?.lock_version ?? state?.lock_version;
  return version !== undefined && version >= MIN_LOCK_VERSION ? version : null;
}

function knownRefusal(error: unknown): string | null {
  if (!(error instanceof ApiError) || typeof error.detail !== "string") {
    return null;
  }
  return RETRY_REFUSAL_CODES.has(error.detail) ? error.detail : null;
}

function isConflict(error: unknown): boolean {
  return error instanceof ApiError && error.status === HTTP_STATUS.CONFLICT;
}

async function refreshQuietly(refresh: () => Promise<unknown>): Promise<void> {
  try {
    await refresh();
  } catch {
    return;
  }
}

async function readAgain(deps: CarouselRetryRunDeps): Promise<void> {
  const { projectId, queryClient } = deps;
  await queryClient.invalidateQueries({
    queryKey: [RETRY_QUERY_KEY, projectId],
  });
  await refreshQuietly(deps.refreshWorkflow);
}

async function handleRefused(
  error: unknown,
  deps: CarouselRetryRunDeps,
): Promise<void> {
  const code = knownRefusal(error);
  const message = deps.translate(
    code ? `refusals.${code}` : "errors.actionFailed",
  );
  deps.setRefusal({ message, stateKey: deps.stateKey });
  deps.showToast(message, RETRY_TOAST_VARIANT.ERROR);
  if (!isConflict(error)) return;
  if (code === RETRY_REFUSAL.USE_REPROCESS) {
    await deps.queryClient.invalidateQueries({
      queryKey: carouselReprocessKeys.detail(deps.projectId),
    });
  }
  await readAgain(deps);
}

async function submitRetry(
  version: number,
  deps: CarouselRetryRunDeps,
): Promise<void> {
  const response = await postCarouselRetry(deps.projectId, version);
  if (response.phase_status === WORKFLOW_PHASE_STATUS.IN_PROGRESS) {
    deps.runWatchRef.current = version;
  }
  deps.showToast(deps.translate("accepted"), RETRY_TOAST_VARIANT.SUCCESS);
  await readAgain(deps);
}

async function runCarouselRetry(deps: CarouselRetryRunDeps): Promise<void> {
  const version = usableVersion(deps.capability, deps.workflowState);
  if (deps.inFlightRef.current || version === null) return;
  if (!deps.enabled || !deps.capability?.can_retry) return;
  deps.inFlightRef.current = true;
  deps.setPending(true);
  deps.setRefusal(null);
  try {
    await submitRetry(version, deps);
  } catch (error: unknown) {
    await handleRefused(error, deps);
  } finally {
    deps.inFlightRef.current = false;
    deps.setPending(false);
  }
}

function useRetryToast(): {
  toast: CarouselRetryToast | null;
  showToast: ShowCarouselRetryToast;
  dismissToast: () => void;
} {
  const nextId = useRef(0);
  const [toast, setToast] = useState<CarouselRetryToast | null>(null);
  const showToast = useCallback<ShowCarouselRetryToast>((message, variant) => {
    nextId.current += 1;
    setToast({ id: nextId.current, message, variant });
  }, []);
  const dismissToast = useCallback((): void => setToast(null), []);
  return { toast, showToast, dismissToast };
}

/**
 * Says how the accepted run ended, once. The watch holds the version the Retry
 * moved past, so only a state past it belongs to this run or a later one, and
 * the stream and the 202 can arrive in either order. The first stop ends the
 * watch, with or without a toast, so a later run never reaches it.
 */
function useRunOutcomeToast(
  workflowState: CarouselRetryWorkflowState | null,
  runWatchRef: React.RefObject<number | null>,
  showToast: ShowCarouselRetryToast,
): void {
  const t = useTranslations("workflow.retry");
  const phaseStatus = workflowState?.phase_status;
  const lockVersion = workflowState?.lock_version;
  useEffect(() => {
    const watched = runWatchRef.current;
    if (watched === null || lockVersion === undefined) return;
    if (lockVersion <= watched) return;
    if (phaseStatus === WORKFLOW_PHASE_STATUS.IN_PROGRESS) return;
    runWatchRef.current = null;
    const outcome = OUTCOME_BY_STATUS[phaseStatus ?? ""];
    if (outcome) showToast(t(outcome.key), outcome.variant);
  }, [phaseStatus, lockVersion, runWatchRef, showToast, t]);
}

/** A temporary refusal is polled, unless the running phase's end re-keys it. */
function shouldPollCapability(
  refusalCode: string | null | undefined,
  phaseStatus: string | undefined,
): boolean {
  if (phaseStatus === WORKFLOW_PHASE_STATUS.IN_PROGRESS) return false;
  return RETRY_TEMPORARY_REFUSALS.has(refusalCode ?? "");
}

function useRetryCapability(
  { projectId, enabled, workflowState }: UseCarouselRetryOptions,
  stateKey: string,
): CarouselRetryCapability | null {
  const query = useQuery({
    queryKey: [RETRY_QUERY_KEY, projectId, stateKey],
    queryFn: (): Promise<CarouselRetryCapability> =>
      fetchCarouselRetryCapability(projectId),
    enabled,
    retry: false,
    refetchInterval: (current): number | false =>
      shouldPollCapability(
        current.state.data?.refusal_code,
        workflowState?.phase_status,
      )
        ? WORKFLOW_BOARD_POLL_INTERVAL_MS
        : false,
  });
  return query.data ?? null;
}

/** The refusal text, the error and whether the Retry can run now. */
function useRetryAvailability(
  options: UseCarouselRetryOptions,
  capability: CarouselRetryCapability | null,
  stateKey: string,
) {
  const [refusal, setRefusal] = useState<CarouselRetryRefusal | null>(null);
  const error = refusal?.stateKey === stateKey ? refusal.message : null;
  const offered = options.enabled && capability?.can_retry === true;
  const hasVersion = usableVersion(capability, options.workflowState) !== null;
  return { error, offered, ready: offered && hasVersion, setRefusal };
}

/** The owner's Retry: the capability, one guarded POST and its toasts. */
export function useCarouselRetry(
  options: UseCarouselRetryOptions,
): CarouselRetryState {
  const t = useTranslations("workflow.retry");
  const queryClient = useQueryClient();
  const inFlightRef = useRef(false);
  const runWatchRef = useRef<number | null>(null);
  const [pending, setPending] = useState(false);
  const { toast, showToast, dismissToast } = useRetryToast();
  const stateKey = workflowStateKey(options.workflowState);
  const capability = useRetryCapability(options, stateKey);
  const { error, offered, ready, setRefusal } = useRetryAvailability(
    options,
    capability,
    stateKey,
  );
  useRunOutcomeToast(options.workflowState, runWatchRef, showToast);
  const retry = (): Promise<void> =>
    runCarouselRetry({
      ...options,
      capability,
      queryClient,
      stateKey,
      inFlightRef,
      runWatchRef,
      translate: t,
      showToast,
      setPending,
      setRefusal,
    });
  return {
    capability,
    pending,
    canSubmit: ready && !pending,
    error,
    visible: offered || pending || error !== null,
    toast,
    dismissToast,
    retry,
  };
}
