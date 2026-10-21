/**
 * The editorial workflow SSE stream, as plain functions — which
 * events it listens to, how an event updates the workflow state, and the
 * ready-confirmation rule. Split out of
 * ``useEditorialWorkflowSse`` unchanged.
 */
import { API_ENDPOINTS } from "@/constants/api";
import { EDITORIAL_WORKFLOW_SSE_EVENTS } from "@/constants/editorial-workflow";
import { WORKFLOW_PHASE_STATUS } from "@/constants/workflow";
import type { EditorialWorkflowState } from "@/modules/editorial/workspace/types-ai";
import {
  appendUniquePhase,
  mergeWorkflowState,
  normalizeProgressPayload,
  parseWorkflowEvent,
  resolveWorkflowEventPayload,
} from "../hooks/use-editorial-workflow-utils";
import type {
  UseEditorialWorkflowSseParams,
  WorkflowEventPayload,
  WorkflowStreamRefs,
} from "../hooks/types";

/** Every named event the stream sends (including the run lifecycle). */
const STREAM_EVENT_NAMES = [
  EDITORIAL_WORKFLOW_SSE_EVENTS.PHASE_CHANGED,
  EDITORIAL_WORKFLOW_SSE_EVENTS.PROGRESS,
  EDITORIAL_WORKFLOW_SSE_EVENTS.REVIEW_REQUIRED,
  EDITORIAL_WORKFLOW_SSE_EVENTS.ERROR,
  EDITORIAL_WORKFLOW_SSE_EVENTS.ARTIFACT,
  EDITORIAL_WORKFLOW_SSE_EVENTS.RUN_STARTED,
  EDITORIAL_WORKFLOW_SSE_EVENTS.RUN_STAGE_CHANGED,
  EDITORIAL_WORKFLOW_SSE_EVENTS.RUN_FINISHED,
] as const;

/** Events that always change the state even without phase fields. */
const STATE_EVENTS: ReadonlySet<string> = new Set([
  EDITORIAL_WORKFLOW_SSE_EVENTS.RUN_STARTED,
  EDITORIAL_WORKFLOW_SSE_EVENTS.RUN_STAGE_CHANGED,
  EDITORIAL_WORKFLOW_SSE_EVENTS.RUN_FINISHED,
  EDITORIAL_WORKFLOW_SSE_EVENTS.REVIEW_REQUIRED,
  EDITORIAL_WORKFLOW_SSE_EVENTS.ARTIFACT,
]);

/** What applying one stream event needs. */
export type StreamEventContext = Pick<
  UseEditorialWorkflowSseParams,
  "projectId" | "setState" | "setPhaseEvents" | "setError" | "refreshState"
> &
  Pick<WorkflowStreamRefs, "workflowStateRef" | "phaseStatusRef">;

/**
 * The stream's connect-time snapshot reads the raw checkpoint,
 * which still says awaiting_human while a resumed run executes (the DB row says
 * in_progress) on the SAME phase. A running -> ready flip on the same phase is
 * therefore confirmed against GET workflow/state (the DB-merged source of
 * truth) before it is applied, so a reload mid-run keeps the running banner and
 * hides the actions. A flip to another phase is a real new gate: applied as is.
 */
export function needsReadyConfirmation(
  prev: EditorialWorkflowState | null,
  next: EditorialWorkflowState,
): boolean {
  return (
    prev?.phase_status === WORKFLOW_PHASE_STATUS.IN_PROGRESS &&
    next.phase_status === WORKFLOW_PHASE_STATUS.AWAITING_HUMAN &&
    prev.current_phase === next.current_phase
  );
}

/** True when the event carries anything that changes the workflow state. */
export function changesWorkflowState(resolved: WorkflowEventPayload): boolean {
  if (resolved.phase || resolved.current_phase || resolved.phase_status) {
    return true;
  }
  if (normalizeProgressPayload(resolved)) {
    return true;
  }
  return resolved.event !== undefined && STATE_EVENTS.has(resolved.event);
}

function applyStreamError(
  payload: WorkflowEventPayload,
  setError: StreamEventContext["setError"],
): void {
  if (payload.recoverable) {
    return;
  }
  if (typeof payload.message === "string" && payload.message.trim()) {
    setError(payload.message);
  }
}

/** Fold one stream event into the workflow state (or the error). */
export function applyWorkflowEvent(
  payload: WorkflowEventPayload,
  ctx: StreamEventContext,
): void {
  if (payload.event === EDITORIAL_WORKFLOW_SSE_EVENTS.ERROR) {
    applyStreamError(payload, ctx.setError);
    return;
  }
  const resolved = resolveWorkflowEventPayload(payload);
  const phase = resolved.phase ?? resolved.current_phase;
  if (phase) {
    ctx.setPhaseEvents((prev) => appendUniquePhase(prev, phase));
  }
  if (!changesWorkflowState(resolved)) {
    return;
  }
  const merged = mergeWorkflowState(
    ctx.projectId,
    ctx.workflowStateRef.current,
    resolved,
  );
  if (needsReadyConfirmation(ctx.workflowStateRef.current, merged)) {
    void ctx.refreshState();
    return;
  }
  ctx.workflowStateRef.current = merged;
  ctx.phaseStatusRef.current = merged.phase_status;
  ctx.setState(merged);
}

/** The callbacks of one stream connection. */
export interface StreamConnectionHandlers {
  onEvent: (payload: WorkflowEventPayload) => void;
  onOpen: () => void;
  onError: (source: EventSource) => void;
}

/**
 * Open the workflow stream and route every event to ``onEvent``.
 *
 * EventSource hides the status of a failed stream, so the reconnect hook probes
 * auth before (and instead of) reconnecting.
 */
export function openWorkflowStream(
  projectId: string,
  { onEvent, onOpen, onError }: StreamConnectionHandlers,
): EventSource {
  const source = new EventSource(
    API_ENDPOINTS.CAROUSEL_WORKFLOW_STREAM(projectId),
    { withCredentials: true },
  );
  const handleMessage = (event: MessageEvent<string>): void => {
    const payload = parseWorkflowEvent(event.data);
    if (payload) {
      onEvent(payload);
    }
  };
  for (const name of STREAM_EVENT_NAMES) {
    source.addEventListener(name, handleMessage);
  }
  source.onmessage = handleMessage;
  source.onopen = onOpen;
  source.onerror = () => onError(source);
  return source;
}

/** What (re)opening the workflow stream needs. */
export interface StartStreamDeps {
  eventContext: StreamEventContext;
  stopPollingFallback: () => void;
  handleStreamOpen: () => void;
  handleStreamError: () => void;
}
