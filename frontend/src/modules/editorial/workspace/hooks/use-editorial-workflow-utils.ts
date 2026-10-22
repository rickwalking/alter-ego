/** Shared helpers for editorial workflow SSE/state merging. */

import {
  EDITORIAL_WORKFLOW_RESUME_CLIENT_ERROR_STATUSES,
  EDITORIAL_WORKFLOW_SSE_EVENTS,
  WORKFLOW_ARTIFACT_FIELD_MAP,
} from "@/constants/editorial-workflow";
import { HTTP_STATUS } from "@/constants/api";
import { WORKFLOW_PHASE_STATUS } from "@/constants/workflow";
import type {
  EditorialWorkflowState,
  WorkflowPhaseStatus,
} from "@/modules/editorial/workspace/types-ai";
import type {
  EditorialWorkflowResumeAcceptedResponse,
  WorkflowEventPayload,
} from "./types";

export type {
  EditorialWorkflowResumeAcceptedResponse,
  WorkflowEventPayload,
} from "./types";

export {
  hasPhaseArtifacts,
  isWorkflowReady,
  waitUntilWorkflowReadyWithTransport,
} from "./workflow-readiness";

export async function readApiError(
  response: Response,
  fallback: string,
): Promise<string> {
  try {
    const payload = (await response.json()) as {
      detail?: string | { msg?: string }[];
    };
    if (typeof payload.detail === "string") {
      return payload.detail;
    }
    if (Array.isArray(payload.detail)) {
      const messages = payload.detail
        .map((item) => item.msg)
        .filter((msg): msg is string => Boolean(msg));
      if (messages.length > 0) {
        return messages.join(", ");
      }
    }
  } catch {}
  return fallback;
}

export function appendUniquePhase(
  phases: string[],
  phase: string | undefined,
): string[] {
  if (!phase || phases.includes(phase)) {
    return phases;
  }
  return [...phases, phase];
}

const PROGRESS_PAYLOAD_KEYS = [
  "current",
  "total",
  "slides",
  "label",
  "message",
  "percent",
] as const;

function pickProgressFields(
  payload: WorkflowEventPayload,
): Record<string, unknown> | null {
  const picked: Record<string, unknown> = {};
  for (const key of PROGRESS_PAYLOAD_KEYS) {
    const value = payload[key];
    if (value !== undefined) {
      picked[key] = value;
    }
  }
  return Object.keys(picked).length > 0 ? picked : null;
}

export function normalizeProgressPayload(
  payload: WorkflowEventPayload,
): Record<string, unknown> | null | undefined {
  if (payload.phase_progress && typeof payload.phase_progress === "object") {
    return payload.phase_progress;
  }
  if (
    payload.event === EDITORIAL_WORKFLOW_SSE_EVENTS.PROGRESS ||
    pickProgressFields(payload) !== null
  ) {
    return pickProgressFields(payload);
  }
  return undefined;
}

function resolveArtifactPayload(
  payload: WorkflowEventPayload,
): WorkflowEventPayload | null {
  if (payload.event !== EDITORIAL_WORKFLOW_SSE_EVENTS.ARTIFACT) {
    return null;
  }
  const artifactType = payload.artifact_type;
  const artifactField =
    artifactType !== undefined
      ? WORKFLOW_ARTIFACT_FIELD_MAP[artifactType]
      : undefined;
  if (!artifactField || payload.data === undefined) {
    return null;
  }
  return { ...payload, [artifactField]: payload.data };
}

function resolveGatePayload(
  payload: WorkflowEventPayload,
): WorkflowEventPayload {
  const gate = payload.gate_payload;
  if (
    payload.event !== EDITORIAL_WORKFLOW_SSE_EVENTS.REVIEW_REQUIRED ||
    !gate ||
    typeof gate !== "object"
  ) {
    return payload;
  }
  return {
    ...payload,
    ...gate,
    phase: payload.phase ?? (gate.current_phase as string | undefined),
    phase_status:
      payload.phase_status ?? (gate.phase_status as string | undefined),
  };
}

export function resolveWorkflowEventPayload(
  payload: WorkflowEventPayload,
): WorkflowEventPayload {
  return resolveArtifactPayload(payload) ?? resolveGatePayload(payload);
}

/**
 * The fields `isFullWorkflowState` actually verifies. `project_id` and
 * `current_phase` may still be absent (the phase can arrive as `phase`).
 */
type FullWorkflowPayload = WorkflowEventPayload &
  Pick<
    EditorialWorkflowState,
    "phase_status" | "research_findings" | "outline" | "slide_drafts"
  >;

function isFullWorkflowState(
  payload: WorkflowEventPayload,
  projectId: string,
): payload is FullWorkflowPayload {
  const resolvedPhase = payload.current_phase ?? payload.phase;
  return (
    (payload.project_id === projectId || !payload.project_id) &&
    typeof resolvedPhase === "string" &&
    typeof payload.phase_status === "string" &&
    Array.isArray(payload.research_findings) &&
    Array.isArray(payload.outline) &&
    Array.isArray(payload.slide_drafts)
  );
}

/**
 * Run metadata merge — run.finished ends the run (fields cleared);
 * other events carry forward the payload's run fields or the previous state.
 */
function mergeRunMetadata(
  prev: EditorialWorkflowState | null,
  payload: WorkflowEventPayload,
): Pick<EditorialWorkflowState, "run_started_at" | "run_stage"> {
  if (payload.event === EDITORIAL_WORKFLOW_SSE_EVENTS.RUN_FINISHED) {
    return { run_started_at: null, run_stage: null };
  }
  return {
    run_started_at: payload.run_started_at ?? prev?.run_started_at ?? null,
    run_stage: payload.run_stage ?? prev?.run_stage ?? null,
  };
}

type CarriedWorkflowFields = Omit<
  EditorialWorkflowState,
  | "project_id"
  | "current_phase"
  | "phase_status"
  | "research_findings"
  | "outline"
  | "slide_drafts"
  | "run_started_at"
  | "run_stage"
>;

type CarryKey = keyof CarriedWorkflowFields & keyof WorkflowEventPayload;

function carry<K extends CarryKey>(
  prev: EditorialWorkflowState | null,
  payload: WorkflowEventPayload,
  key: K,
): (WorkflowEventPayload & EditorialWorkflowState)[K] | undefined {
  return (
    (payload as WorkflowEventPayload & EditorialWorkflowState)[key] ??
    prev?.[key]
  );
}

function mergeDefaultedFields(
  prev: EditorialWorkflowState | null,
  payload: WorkflowEventPayload,
): Pick<
  CarriedWorkflowFields,
  | "slide_image_prompts"
  | "image_assets"
  | "design_applied"
  | "phase_progress"
  | "status"
> {
  return {
    slide_image_prompts: carry(prev, payload, "slide_image_prompts") ?? null,
    image_assets: carry(prev, payload, "image_assets") ?? [],
    design_applied: carry(prev, payload, "design_applied") ?? false,
    phase_progress:
      normalizeProgressPayload(payload) ??
      carry(prev, payload, "phase_progress") ??
      null,
    status: carry(prev, payload, "status") ?? "draft",
  };
}

const OPTIONAL_CARRIED_KEYS = [
  "rubric_scores",
  "persona_scores",
  "caption",
  "blog_markdown",
  "linkedin_post_pt",
  "linkedin_post_en",
  "workflow_status",
  "presentation_policy_version",
  "localized_slides",
  "lock_version",
  "presentation_validation",
] as const satisfies readonly CarryKey[];

function mergeOptionalFields(
  prev: EditorialWorkflowState | null,
  payload: WorkflowEventPayload,
): Partial<CarriedWorkflowFields> {
  return Object.fromEntries(
    OPTIONAL_CARRIED_KEYS.map((key) => [key, carry(prev, payload, key)]),
  );
}

/**
 * Fields every event carries forward: the payload's value, else the previous
 * state's (never drop the CAS ``lock_version`` the actions send).
 */
function mergeCarriedFields(
  prev: EditorialWorkflowState | null,
  payload: WorkflowEventPayload,
): CarriedWorkflowFields {
  return {
    ...mergeOptionalFields(prev, payload),
    ...mergeDefaultedFields(prev, payload),
  };
}

type ListKey = "research_findings" | "outline" | "slide_drafts";

function carryList<K extends ListKey>(
  prev: EditorialWorkflowState | null,
  payload: WorkflowEventPayload,
  key: K,
): EditorialWorkflowState[K] {
  return payload[key] ?? prev?.[key] ?? [];
}

function mergePartialLists(
  prev: EditorialWorkflowState | null,
  payload: WorkflowEventPayload,
): Pick<EditorialWorkflowState, ListKey> {
  return {
    research_findings: carryList(prev, payload, "research_findings"),
    outline: carryList(prev, payload, "outline"),
    slide_drafts: carryList(prev, payload, "slide_drafts"),
  };
}

function mergePartialCore(
  projectId: string,
  prev: EditorialWorkflowState | null,
  payload: WorkflowEventPayload,
): Pick<
  EditorialWorkflowState,
  | "project_id"
  | "current_phase"
  | "phase_status"
  | "research_findings"
  | "outline"
  | "slide_drafts"
> {
  return {
    ...mergePartialLists(prev, payload),
    project_id: projectId,
    current_phase:
      payload.phase ?? payload.current_phase ?? prev?.current_phase ?? "",
    phase_status: (payload.phase_status ??
      prev?.phase_status ??
      "") as WorkflowPhaseStatus,
  };
}

export function mergeWorkflowState(
  projectId: string,
  prev: EditorialWorkflowState | null,
  payload: WorkflowEventPayload,
): EditorialWorkflowState {
  const carried = {
    ...mergeRunMetadata(prev, payload),
    ...mergeCarriedFields(prev, payload),
  };

  if (!isFullWorkflowState(payload, projectId)) {
    return { ...carried, ...mergePartialCore(projectId, prev, payload) };
  }
  return {
    ...carried,
    project_id: payload.project_id ?? projectId,
    current_phase: payload.current_phase ?? payload.phase ?? "",
    phase_status: payload.phase_status,
    research_findings: payload.research_findings,
    outline: payload.outline,
    slide_drafts: payload.slide_drafts,
  };
}

export function parseWorkflowEvent(data: string): WorkflowEventPayload | null {
  try {
    return JSON.parse(data) as WorkflowEventPayload;
  } catch {
    return null;
  }
}

export function shouldPollWorkflowState(
  phaseStatus: string | undefined,
  transportMode: string,
  pollingFallbackMode: string,
): boolean {
  if (transportMode !== pollingFallbackMode) {
    return false;
  }
  return phaseStatus !== WORKFLOW_PHASE_STATUS.AWAITING_HUMAN;
}

export function isResumeClientErrorStatus(status: number): boolean {
  return EDITORIAL_WORKFLOW_RESUME_CLIENT_ERROR_STATUSES.includes(
    status as (typeof EDITORIAL_WORKFLOW_RESUME_CLIENT_ERROR_STATUSES)[number],
  );
}

export function isResumeTransportFailure(status: number): boolean {
  return (
    status === HTTP_STATUS.INTERNAL_SERVER_ERROR ||
    status === HTTP_STATUS.BAD_GATEWAY ||
    status === HTTP_STATUS.SERVICE_UNAVAILABLE ||
    status === HTTP_STATUS.GATEWAY_TIMEOUT
  );
}

export function isResumeAcceptedResponse(
  payload: unknown,
): payload is EditorialWorkflowResumeAcceptedResponse {
  if (!payload || typeof payload !== "object") {
    return false;
  }
  const record = payload as Record<string, unknown>;
  return (
    record.accepted === true &&
    typeof record.project_id === "string" &&
    typeof record.current_phase === "string" &&
    typeof record.phase_status === "string" &&
    typeof record.lock_version === "number"
  );
}
