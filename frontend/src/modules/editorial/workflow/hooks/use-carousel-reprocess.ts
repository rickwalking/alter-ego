"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseQueryResult,
} from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { HTTP_STATUS } from "@/constants/api";
import {
  QUEUE_STATUS,
  REPROCESS_POLL_INTERVAL_MS,
  REPROCESS_REFUSAL_CODES,
  WORKFLOW_BOARD_POLL_INTERVAL_MS,
} from "@/constants/workflow";
import { ApiError } from "@/lib/api-client";
import { generationLogKey } from "@/modules/editorial/workspace/hooks/use-generation-log";
import type {
  CarouselReprocessCapability,
  ManualReprocessResponse,
} from "@/schemas/carousel-reprocess";
import {
  fetchCarouselReprocessCapability,
  postCarouselReprocess,
} from "./carousel-reprocess-requests";
import type {
  CarouselReprocessActionState,
  CarouselReprocessErrorDeps,
  CarouselReprocessRequest,
  CarouselReprocessRunDeps,
  CarouselReprocessState,
  UseCarouselReprocessOptions,
} from "./types";

const ACTIVE_STATUSES: ReadonlySet<string> = new Set([
  QUEUE_STATUS.QUEUED,
  QUEUE_STATUS.RUNNING,
  QUEUE_STATUS.RETRY_WAIT,
]);
const MIN_LOCK_VERSION = 1;
const carouselReprocessKeys = {
  detail: (projectId: string) => ["carousel-reprocess", projectId] as const,
};

function isStatus(error: unknown, status: number): boolean {
  return error instanceof ApiError && error.status === status;
}

function isProgressVisible(
  capability: CarouselReprocessCapability | null,
  runId: string | null,
): boolean {
  return (
    runId !== null &&
    capability?.run_id === runId &&
    capability.status !== null &&
    ACTIVE_STATUSES.has(capability.status)
  );
}

function queryPollInterval(
  capability: CarouselReprocessCapability | undefined,
  error: unknown,
  progressRunId: string | null,
): number | false {
  let interval: number | false = false;
  if (
    !isStatus(error, HTTP_STATUS.FORBIDDEN) &&
    capability?.status &&
    ACTIVE_STATUSES.has(capability.status)
  ) {
    const tracking =
      progressRunId !== null && capability.run_id === progressRunId;
    interval =
      capability.stuck_kind === null && !tracking
        ? WORKFLOW_BOARD_POLL_INTERVAL_MS
        : REPROCESS_POLL_INTERVAL_MS;
  }
  return interval;
}

function refusalCode(error: unknown): string | null {
  if (
    !isStatus(error, HTTP_STATUS.CONFLICT) ||
    !(error instanceof ApiError) ||
    typeof error.detail !== "string" ||
    !REPROCESS_REFUSAL_CODES.has(error.detail)
  ) {
    return null;
  }
  return error.detail;
}

function acceptedCapability(
  response: ManualReprocessResponse,
  previous: CarouselReprocessCapability | undefined,
): CarouselReprocessCapability {
  return {
    can_reprocess: false,
    refusal_code: null,
    stuck_kind: response.stuck_kind,
    run_id: response.run_id,
    status: response.status,
    last_phase: previous?.last_phase ?? null,
    last_error_code: response.last_error_code,
    position: response.position,
    eta_seconds: response.eta_seconds,
    lock_version: response.lock_version,
  };
}

async function refreshAfterChange(
  refreshWorkflow: () => Promise<unknown>,
): Promise<void> {
  try {
    await refreshWorkflow();
  } catch {
    return;
  }
}

function hasExpectedVersion(version: number | undefined): version is number {
  return version !== undefined && version >= MIN_LOCK_VERSION;
}

function errorMessage(
  error: unknown,
  translate: CarouselReprocessErrorDeps["translate"],
): string {
  if (isStatus(error, HTTP_STATUS.FORBIDDEN)) {
    return translate("errors.forbidden");
  }
  const refusal = refusalCode(error);
  if (refusal) return translate(`refusals.${refusal}`);
  return translate("errors.actionFailed");
}

async function handleReprocessError(
  error: unknown,
  deps: CarouselReprocessErrorDeps,
): Promise<void> {
  deps.setActionError(errorMessage(error, deps.translate));
  if (!isStatus(error, HTTP_STATUS.CONFLICT)) return;
  await deps.queryClient.invalidateQueries({
    queryKey: carouselReprocessKeys.detail(deps.projectId),
  });
  await refreshAfterChange(deps.refreshWorkflow);
}

function canStart(
  current: CarouselReprocessCapability | null,
  deps: CarouselReprocessRunDeps,
): current is CarouselReprocessCapability {
  return (
    !deps.inFlightRef.current && deps.enabled && current?.can_reprocess === true
  );
}

async function runCarouselReprocess(
  deps: CarouselReprocessRunDeps,
): Promise<void> {
  const key = carouselReprocessKeys.detail(deps.projectId);
  const current =
    deps.queryClient.getQueryData<CarouselReprocessCapability>(key) ??
    deps.capability;
  if (!canStart(current, deps)) return;
  const version = current.lock_version ?? deps.fallbackExpectedVersion;
  if (!hasExpectedVersion(version)) return;
  deps.inFlightRef.current = true;
  deps.setPending(true);
  deps.setActionError(null);
  try {
    const response = await deps.mutateAsync({
      expectedVersion: version,
      runId: current.run_id,
    });
    deps.markProgressRequested(response.run_id);
  } catch (error: unknown) {
    await handleReprocessError(error, deps);
  } finally {
    deps.inFlightRef.current = false;
    deps.setPending(false);
  }
}

function useGenerationLogPollRefresh(
  projectId: string,
  dataUpdatedAt: number,
): void {
  const queryClient = useQueryClient();
  const previousUpdate = useRef(dataUpdatedAt);
  const hasData = useRef(dataUpdatedAt > 0);
  useEffect(() => {
    if (dataUpdatedAt === 0 || previousUpdate.current === dataUpdatedAt) {
      return;
    }
    previousUpdate.current = dataUpdatedAt;
    if (!hasData.current) {
      hasData.current = true;
      return;
    }
    void queryClient.invalidateQueries({
      queryKey: generationLogKey(projectId),
    });
  }, [dataUpdatedAt, projectId, queryClient]);
}

function useReprocessQuery(
  projectId: string,
  enabled: boolean,
  progressRunId: string | null,
): UseQueryResult<CarouselReprocessCapability> {
  return useQuery({
    queryKey: carouselReprocessKeys.detail(projectId),
    queryFn: (): Promise<CarouselReprocessCapability> =>
      fetchCarouselReprocessCapability(projectId),
    enabled,
    retry: false,
    refetchInterval: (current): number | false =>
      queryPollInterval(current.state.data, current.state.error, progressRunId),
    refetchOnWindowFocus: false,
  });
}

function useReprocessMutation(
  projectId: string,
  queryClient: ReturnType<typeof useQueryClient>,
  refreshWorkflow: () => Promise<unknown>,
): (input: CarouselReprocessRequest) => Promise<ManualReprocessResponse> {
  const { mutateAsync } = useMutation({
    mutationFn: (
      input: CarouselReprocessRequest,
    ): Promise<ManualReprocessResponse> =>
      postCarouselReprocess(projectId, input),
    onSuccess: async (response): Promise<void> => {
      const key = carouselReprocessKeys.detail(projectId);
      const previous =
        queryClient.getQueryData<CarouselReprocessCapability>(key);
      queryClient.setQueryData(key, acceptedCapability(response, previous));
      await refreshAfterChange(refreshWorkflow);
    },
  });
  return mutateAsync;
}

function useReprocessAction(
  options: UseCarouselReprocessOptions,
  capability: CarouselReprocessCapability | null,
  markProgressRequested: (runId: string) => void,
): CarouselReprocessActionState {
  const { projectId, enabled, fallbackExpectedVersion, refreshWorkflow } =
    options;
  const t = useTranslations("workflow.reprocess");
  const queryClient = useQueryClient();
  const inFlightRef = useRef(false);
  const [pending, setPending] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const mutateAsync = useReprocessMutation(
    projectId,
    queryClient,
    refreshWorkflow,
  );
  const expectedVersion = capability?.lock_version ?? fallbackExpectedVersion;
  const canSubmit =
    enabled &&
    capability?.can_reprocess === true &&
    hasExpectedVersion(expectedVersion);
  const reprocess = useCallback(
    (): Promise<void> =>
      runCarouselReprocess({
        ...options,
        capability,
        queryClient,
        inFlightRef,
        setPending,
        markProgressRequested,
        setActionError,
        mutateAsync,
        translate: t,
      }),
    [capability, markProgressRequested, mutateAsync, options, queryClient, t],
  );
  return { pending, canSubmit, actionError, reprocess };
}

/** Owner/admin recovery capability, one idempotent POST, and active-run polling. */
export function useCarouselReprocess(
  options: UseCarouselReprocessOptions,
): CarouselReprocessState {
  const t = useTranslations("workflow.reprocess");
  const [progressRunId, setProgressRunId] = useState<string | null>(null);
  const markProgressRequested = useCallback((runId: string): void => {
    setProgressRunId(runId);
  }, []);
  const query = useReprocessQuery(
    options.projectId,
    options.enabled,
    progressRunId,
  );
  useGenerationLogPollRefresh(options.projectId, query.dataUpdatedAt);
  const forbidden = isStatus(query.error, HTTP_STATUS.FORBIDDEN);
  const capability = forbidden ? null : (query.data ?? null);
  const action = useReprocessAction(options, capability, markProgressRequested);
  const loadError = query.isError && !forbidden ? t("errors.loadFailed") : null;
  return {
    capability,
    pending: action.pending,
    forbidden,
    canSubmit: action.canSubmit,
    error: action.actionError ?? loadError,
    progressVisible: isProgressVisible(capability, progressRunId),
    reprocess: action.reprocess,
  };
}
