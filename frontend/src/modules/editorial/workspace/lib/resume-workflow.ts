/**
 * AE-0446: the steps of an editorial resume (approve / revise / send back),
 * split out of ``useEditorialWorkflowResume`` unchanged: same payload, same
 * response handling order, same state updates.
 */
import { API_ENDPOINTS, HTTP_METHODS, HTTP_STATUS } from "@/constants/api";
import {
  EDITORIAL_RESUME_ERROR_CODES,
  EDITORIAL_WORKFLOW_CONFLICT_CODES,
  EDITORIAL_WORKFLOW_TRANSPORT_MODE,
} from "@/constants/editorial-workflow";
import { WORKFLOW_PHASE_STATUS } from "@/constants/workflow";
import type {
  EditorialWorkflowState,
  LocalizedSlideReview,
  WorkflowPhaseStatus,
} from "@/modules/editorial/workspace/types-ai";
import { authenticatedFetch } from "@/lib/authenticated-fetch";
import {
  appendUniquePhase,
  isResumeAcceptedResponse,
  isResumeClientErrorStatus,
  isResumeTransportFailure,
  isWorkflowReady,
  readApiError,
  waitUntilWorkflowReadyWithTransport,
} from "../hooks/use-editorial-workflow-utils";
import type {
  EditorialReviseOptions,
  EditorialWorkflowResumeAcceptedResponse,
  UseEditorialWorkflowResumeParams,
} from "../hooks/types";

/** One resume call: the hook's dependencies plus the phase it acted on. */
export interface ResumeContext {
  deps: UseEditorialWorkflowResumeParams;
  actedOnPhase: string | undefined;
}

interface ResumePayload {
  action: string;
  feedback?: string;
  expected_version: number;
  structured_feedback?: {
    target_phase?: string;
    edited_text?: string;
    edited_localized_slides?: LocalizedSlideReview[];
  };
}

/** The request shape of one resume (action, optional feedback and edits). */
export interface ResumeRequest {
  action: string;
  feedback?: string;
  options?: EditorialReviseOptions;
}

// AE-0310/AE-0315: each machine-readable 409 cause gets distinct copy.
const CONFLICT_MESSAGE_KEYS: Readonly<Record<string, string>> = {
  [EDITORIAL_WORKFLOW_CONFLICT_CODES.REVISION_CAP_EXCEEDED]:
    "revisionCapExceeded",
  [EDITORIAL_WORKFLOW_CONFLICT_CODES.VERSION_CONFLICT]: "versionConflict",
  [EDITORIAL_WORKFLOW_CONFLICT_CODES.RUN_IN_PROGRESS]: "runInProgress",
};

/** Translate a known machine code; anything else is shown as sent. */
export function resumeErrorMessage(
  message: string,
  translateError: (key: string) => string,
): string {
  const conflictKey = CONFLICT_MESSAGE_KEYS[message];
  if (conflictKey) {
    return translateError(conflictKey);
  }
  // AE-0414 (B02): a known 4xx code is translated, never shown raw.
  if (EDITORIAL_RESUME_ERROR_CODES.has(message)) {
    return translateError(`resumeCodes.${message}`);
  }
  return message;
}

/**
 * AE-0415: a ready gate on another phase than the one the owner acted on is a
 * newer result (the stream delivered it before the 202) and must be kept.
 */
function isNewerReadyGate(
  state: EditorialWorkflowState,
  actedOnPhase: string | undefined,
): boolean {
  return isWorkflowReady(state) && state.current_phase !== actedOnPhase;
}

/** Optimistically mark a non-ready gate as running while the request flies. */
export function markResumeRunning({ deps }: ResumeContext): void {
  deps.setState((prev) => {
    if (!prev || isWorkflowReady(prev)) {
      return prev;
    }
    const next = { ...prev, phase_status: WORKFLOW_PHASE_STATUS.IN_PROGRESS };
    deps.workflowStateRef.current = next;
    return next;
  });
}

/** An empty string counts as "not sent" (matches the old truthiness checks). */
function nonEmpty(value: string | undefined): string | undefined {
  if (!value) {
    return undefined;
  }
  return value;
}

function structuredFeedback(
  options: EditorialReviseOptions | undefined,
): ResumePayload["structured_feedback"] {
  const fields = {
    target_phase: nonEmpty(options?.targetPhase),
    edited_text: nonEmpty(options?.editedText),
    edited_localized_slides: options?.editedLocalizedSlides?.length
      ? options.editedLocalizedSlides
      : undefined,
  };
  const present = Object.entries(fields).filter(
    ([, value]) => value !== undefined,
  );
  return present.length > 0 ? Object.fromEntries(present) : undefined;
}

/** The POST body (the lock version is re-read when the hook has none). */
export async function buildResumePayload(
  { deps }: ResumeContext,
  { action, feedback, options }: ResumeRequest,
): Promise<ResumePayload> {
  const lockVersion =
    deps.lockVersion ?? (await deps.refreshState())?.lock_version;
  const payload: ResumePayload = {
    action,
    expected_version: lockVersion ?? 1,
  };
  if (feedback !== undefined) {
    payload.feedback = feedback;
  }
  const structured = structuredFeedback(options);
  if (structured) {
    payload.structured_feedback = structured;
  }
  return payload;
}

function waitForReadyState({
  deps,
}: ResumeContext): Promise<EditorialWorkflowState | null> {
  return waitUntilWorkflowReadyWithTransport(
    () => deps.workflowStateRef.current,
    deps.refreshState,
    {
      preferSse:
        deps.transportModeRef.current === EDITORIAL_WORKFLOW_TRANSPORT_MODE.SSE,
    },
  );
}

function adoptReady(
  { deps }: ResumeContext,
  ready: EditorialWorkflowState,
): EditorialWorkflowState {
  if (ready.phase_status === WORKFLOW_PHASE_STATUS.AWAITING_HUMAN) {
    deps.stopPollingFallback();
  }
  return ready;
}

/** Store the answered state; if it is not a ready gate yet, poll for one. */
async function finalizeResume(
  ctx: ResumeContext,
  workflowState: EditorialWorkflowState | null,
): Promise<EditorialWorkflowState> {
  const { deps } = ctx;
  if (!workflowState) {
    throw new Error(deps.translateError("resumeFailed"));
  }
  deps.setState(workflowState);
  deps.workflowStateRef.current = workflowState;
  if (workflowState.current_phase) {
    deps.setPhaseEvents((prev) =>
      appendUniquePhase(prev, workflowState.current_phase),
    );
  }
  if (isWorkflowReady(workflowState)) {
    return adoptReady(ctx, workflowState);
  }
  deps.enterPollingFallback();
  const ready = await waitForReadyState(ctx);
  if (ready && isWorkflowReady(ready)) {
    deps.setState(ready);
    deps.workflowStateRef.current = ready;
    return adoptReady(ctx, ready);
  }
  throw new Error(deps.translateError("resumeFailed"));
}

/**
 * The last resume step, run by the caller AFTER its loading/error handling:
 * a second wait for the gate (or its "resumeFailed") must not keep the
 * actions locked nor raise the resume error (same as before the split).
 */
export type FinishResume = () => Promise<EditorialWorkflowState>;

function finishWith(
  ctx: ResumeContext,
  workflowState: EditorialWorkflowState | null,
): FinishResume {
  return () => finalizeResume(ctx, workflowState);
}

async function pollForReady(ctx: ResumeContext): Promise<FinishResume> {
  ctx.deps.enterPollingFallback();
  return finishWith(ctx, await waitForReadyState(ctx));
}

/**
 * AE-0415 (B26): the backend marked the run in_progress before the 202, so the
 * gate the owner just acted on is no longer ready — adopt the accepted status
 * (running banner, actions hidden) and wait for the NEXT ready state.
 */
async function handleAccepted(
  ctx: ResumeContext,
  response: Response,
): Promise<FinishResume> {
  const { deps, actedOnPhase } = ctx;
  const accepted =
    (await response.json()) as EditorialWorkflowResumeAcceptedResponse;
  if (!isResumeAcceptedResponse(accepted)) {
    throw new Error(deps.translateError("resumeFailed"));
  }
  deps.setState((prev) => {
    const next = prev
      ? isNewerReadyGate(prev, actedOnPhase)
        ? { ...prev, lock_version: accepted.lock_version }
        : {
            ...prev,
            lock_version: accepted.lock_version,
            phase_status: accepted.phase_status as WorkflowPhaseStatus,
          }
      : prev;
    deps.workflowStateRef.current = next;
    return next;
  });
  const current = deps.workflowStateRef.current;
  if (current && isWorkflowReady(current)) {
    return finishWith(ctx, current);
  }
  return finishWith(ctx, await waitForReadyState(ctx));
}

/** 4xx: a run-in-progress 409 shows the banner; anything else throws its copy. */
async function handleClientError(
  { deps }: ResumeContext,
  response: Response,
): Promise<FinishResume> {
  const detail = await readApiError(
    response,
    deps.translateError("resumeFailed"),
  );
  if (
    response.status === HTTP_STATUS.CONFLICT &&
    detail === EDITORIAL_WORKFLOW_CONFLICT_CODES.RUN_IN_PROGRESS
  ) {
    // AE-0315: refresh pulls run_started_at/run_stage so the banner
    // reconstructs from state.
    const refreshed = await deps.refreshState();
    if (refreshed) {
      deps.setState(refreshed);
      deps.workflowStateRef.current = refreshed;
      return () => Promise.resolve(refreshed);
    }
  }
  throw new Error(resumeErrorMessage(detail, deps.translateError));
}

/** Route the resume response by status (same order as before the split). */
async function handleResumeResponse(
  ctx: ResumeContext,
  response: Response,
): Promise<FinishResume> {
  if (response.status === HTTP_STATUS.ACCEPTED) {
    return handleAccepted(ctx, response);
  }
  if (response.ok) {
    return finishWith(ctx, (await response.json()) as EditorialWorkflowState);
  }
  if (isResumeClientErrorStatus(response.status)) {
    return handleClientError(ctx, response);
  }
  if (isResumeTransportFailure(response.status)) {
    return pollForReady(ctx);
  }
  const { translateError } = ctx.deps;
  throw new Error(
    resumeErrorMessage(
      await readApiError(response, translateError("resumeFailed")),
      translateError,
    ),
  );
}

/**
 * POST the resume; a network failure falls back to polling for the gate.
 * Resolves to the finishing step (see ``FinishResume``).
 */
export async function sendResume(
  ctx: ResumeContext,
  request: ResumeRequest,
): Promise<FinishResume> {
  const payload = await buildResumePayload(ctx, request);
  let response: Response;
  try {
    response = await authenticatedFetch(
      API_ENDPOINTS.CAROUSEL_WORKFLOW_RESUME(ctx.deps.projectId),
      { method: HTTP_METHODS.POST, body: JSON.stringify(payload) },
    );
  } catch {
    return pollForReady(ctx);
  }
  return handleResumeResponse(ctx, response);
}
