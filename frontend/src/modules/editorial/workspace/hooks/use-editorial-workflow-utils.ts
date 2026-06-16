/** Shared helpers for editorial workflow SSE/state merging. */

import {
  EDITORIAL_PHASES,
  EDITORIAL_WORKFLOW_RESUME_CLIENT_ERROR_STATUSES,
  EDITORIAL_WORKFLOW_RESUME_POLL_INTERVAL_MS,
  EDITORIAL_WORKFLOW_RESUME_POLL_MAX_ATTEMPTS,
  EDITORIAL_WORKFLOW_SSE_EVENTS,
  WORKFLOW_ARTIFACT_FIELD_MAP,
} from "@/constants/editorial-workflow";
import { HTTP_STATUS } from "@/constants/api";
import { WORKFLOW_PHASE_STATUS } from "@/constants/workflow";
import type { EditorialWorkflowState } from "@/modules/editorial/workspace/types-ai";

export interface WorkflowEventPayload {
  event?: string;
  phase?: string;
  phase_status?: string;
  project_id?: string;
  current_phase?: string;
  current?: number;
  total?: number;
  slides?: Record<string, unknown>[];
  label?: string;
  message?: string;
  percent?: number;
  recoverable?: boolean;
  gate_payload?: Record<string, unknown> | null;
  research_findings?: Record<string, unknown>[];
  outline?: Record<string, unknown>[];
  slide_drafts?: Record<string, unknown>[];
  slide_image_prompts?: EditorialWorkflowState["slide_image_prompts"];
  image_assets?: string[];
  design_applied?: boolean;
  phase_progress?: Record<string, unknown> | null;
  rubric_scores?: Record<string, unknown>;
  persona_scores?: Record<string, unknown>;
  caption?: string;
  blog_markdown?: string;
  linkedin_post_pt?: string;
  linkedin_post_en?: string;
  workflow_status?: string;
  status?: string;
  artifact_type?: string;
  data?: unknown;
  presentation_policy_version?: string | null;
  localized_slides?: EditorialWorkflowState["localized_slides"];
  presentation_validation?: EditorialWorkflowState["presentation_validation"];
}

export interface EditorialWorkflowResumeAcceptedResponse {
  accepted: boolean;
  project_id: string;
  current_phase: string;
  phase_status: string;
  lock_version: number;
}

export async function readApiError(
  response: Response,
  fallback: string,
): Promise<string> {
  try {
    const payload = (await response.json()) as {
      detail?: string | Array<{ msg?: string }>;
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
  } catch {
    // Ignore malformed error payloads.
  }
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

export function resolveWorkflowEventPayload(
  payload: WorkflowEventPayload,
): WorkflowEventPayload {
  if (payload.event === EDITORIAL_WORKFLOW_SSE_EVENTS.ARTIFACT) {
    const artifactType = payload.artifact_type;
    const artifactField =
      artifactType !== undefined
        ? WORKFLOW_ARTIFACT_FIELD_MAP[artifactType]
        : undefined;
    if (artifactField && payload.data !== undefined) {
      return {
        ...payload,
        [artifactField]: payload.data,
      };
    }
  }

  if (
    payload.event !== EDITORIAL_WORKFLOW_SSE_EVENTS.REVIEW_REQUIRED ||
    !payload.gate_payload ||
    typeof payload.gate_payload !== "object"
  ) {
    return payload;
  }
  const gate = payload.gate_payload;
  return {
    ...payload,
    ...gate,
    phase: payload.phase ?? (gate.current_phase as string | undefined),
    phase_status:
      payload.phase_status ?? (gate.phase_status as string | undefined),
  };
}

function isFullWorkflowState(
  payload: WorkflowEventPayload,
  projectId: string,
): payload is WorkflowEventPayload & EditorialWorkflowState {
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

export function mergeWorkflowState(
  projectId: string,
  prev: EditorialWorkflowState | null,
  payload: WorkflowEventPayload,
): EditorialWorkflowState {
  const normalizedProgress = normalizeProgressPayload(payload);

  if (isFullWorkflowState(payload, projectId)) {
    return {
      project_id: payload.project_id ?? projectId,
      current_phase: payload.current_phase ?? payload.phase ?? "",
      phase_status: payload.phase_status,
      research_findings: payload.research_findings,
      outline: payload.outline,
      slide_drafts: payload.slide_drafts,
      slide_image_prompts:
        payload.slide_image_prompts ?? prev?.slide_image_prompts ?? null,
      image_assets: payload.image_assets ?? prev?.image_assets ?? [],
      design_applied: payload.design_applied ?? prev?.design_applied ?? false,
      phase_progress:
        normalizedProgress ??
        payload.phase_progress ??
        prev?.phase_progress ??
        null,
      rubric_scores: payload.rubric_scores ?? prev?.rubric_scores,
      persona_scores: payload.persona_scores ?? prev?.persona_scores,
      caption: payload.caption ?? prev?.caption,
      blog_markdown: payload.blog_markdown ?? prev?.blog_markdown,
      linkedin_post_pt: payload.linkedin_post_pt ?? prev?.linkedin_post_pt,
      linkedin_post_en: payload.linkedin_post_en ?? prev?.linkedin_post_en,
      workflow_status: payload.workflow_status ?? prev?.workflow_status,
      status: payload.status ?? prev?.status ?? "draft",
      presentation_policy_version:
        payload.presentation_policy_version ??
        prev?.presentation_policy_version,
      localized_slides: payload.localized_slides ?? prev?.localized_slides,
      presentation_validation:
        payload.presentation_validation ?? prev?.presentation_validation,
    };
  }

  return {
    project_id: projectId,
    current_phase:
      payload.phase ?? payload.current_phase ?? prev?.current_phase ?? "",
    phase_status: (payload.phase_status ??
      prev?.phase_status ??
      "") as import("@/modules/editorial/workspace/types-ai").WorkflowPhaseStatus,
    research_findings:
      payload.research_findings ?? prev?.research_findings ?? [],
    outline: payload.outline ?? prev?.outline ?? [],
    slide_drafts: payload.slide_drafts ?? prev?.slide_drafts ?? [],
    slide_image_prompts:
      payload.slide_image_prompts ?? prev?.slide_image_prompts ?? null,
    image_assets: payload.image_assets ?? prev?.image_assets ?? [],
    design_applied: payload.design_applied ?? prev?.design_applied ?? false,
    phase_progress:
      normalizedProgress ??
      payload.phase_progress ??
      prev?.phase_progress ??
      null,
    rubric_scores: payload.rubric_scores ?? prev?.rubric_scores,
    persona_scores: payload.persona_scores ?? prev?.persona_scores,
    caption: payload.caption ?? prev?.caption,
    blog_markdown: payload.blog_markdown ?? prev?.blog_markdown,
    linkedin_post_pt: payload.linkedin_post_pt ?? prev?.linkedin_post_pt,
    linkedin_post_en: payload.linkedin_post_en ?? prev?.linkedin_post_en,
    workflow_status: payload.workflow_status ?? prev?.workflow_status,
    status: payload.status ?? prev?.status ?? "draft",
    presentation_policy_version:
      payload.presentation_policy_version ?? prev?.presentation_policy_version,
    localized_slides: payload.localized_slides ?? prev?.localized_slides,
    presentation_validation:
      payload.presentation_validation ?? prev?.presentation_validation,
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

export function hasPhaseArtifacts(state: EditorialWorkflowState): boolean {
  switch (state.current_phase) {
    case EDITORIAL_PHASES.RESEARCH:
      return (state.research_findings?.length ?? 0) > 0;
    case EDITORIAL_PHASES.OUTLINE:
      return (state.outline?.length ?? 0) > 0;
    case EDITORIAL_PHASES.CONTENT: {
      const draftCount = state.slide_drafts?.length ?? 0;
      const outlineCount = state.outline?.length ?? 0;
      return (
        draftCount > 0 && (outlineCount === 0 || draftCount >= outlineCount)
      );
    }
    case EDITORIAL_PHASES.DESIGN:
      return state.design_applied === true;
    case EDITORIAL_PHASES.IMAGES:
      return (state.image_assets?.length ?? 0) > 0;
    case EDITORIAL_PHASES.FINAL_REVIEW:
      return (
        Boolean(state.caption?.trim()) ||
        Boolean(state.blog_markdown?.trim()) ||
        Object.keys(state.rubric_scores ?? {}).length > 0
      );
    default:
      return true;
  }
}

export function isWorkflowReady(state: EditorialWorkflowState): boolean {
  if (
    state.phase_status === WORKFLOW_PHASE_STATUS.FAILED ||
    state.phase_status === WORKFLOW_PHASE_STATUS.REJECTED
  ) {
    return true;
  }
  if (state.phase_status !== WORKFLOW_PHASE_STATUS.AWAITING_HUMAN) {
    return false;
  }
  return hasPhaseArtifacts(state);
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

async function pollUntilWorkflowReady(
  refreshState: () => Promise<EditorialWorkflowState | null>,
  options?: {
    intervalMs?: number;
    maxAttempts?: number;
  },
): Promise<EditorialWorkflowState | null> {
  const intervalMs =
    options?.intervalMs ?? EDITORIAL_WORKFLOW_RESUME_POLL_INTERVAL_MS;
  const maxAttempts =
    options?.maxAttempts ?? EDITORIAL_WORKFLOW_RESUME_POLL_MAX_ATTEMPTS;

  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    const workflowState = await refreshState();
    if (workflowState && isWorkflowReady(workflowState)) {
      return workflowState;
    }
    await new Promise<void>((resolve) => {
      window.setTimeout(resolve, intervalMs);
    });
  }

  const finalState = await refreshState();
  if (finalState && isWorkflowReady(finalState)) {
    return finalState;
  }
  return finalState;
}

export async function waitUntilWorkflowReadyWithTransport(
  getState: () => EditorialWorkflowState | null,
  refreshState: () => Promise<EditorialWorkflowState | null>,
  options: {
    preferSse: boolean;
    intervalMs?: number;
    maxAttempts?: number;
  },
): Promise<EditorialWorkflowState | null> {
  const intervalMs =
    options.intervalMs ?? EDITORIAL_WORKFLOW_RESUME_POLL_INTERVAL_MS;
  const maxAttempts =
    options.maxAttempts ?? EDITORIAL_WORKFLOW_RESUME_POLL_MAX_ATTEMPTS;

  if (options.preferSse) {
    for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
      const current = getState();
      if (current && isWorkflowReady(current)) {
        return current;
      }
      await new Promise<void>((resolve) => {
        window.setTimeout(resolve, intervalMs);
      });
    }
    const final = getState();
    if (final && isWorkflowReady(final)) {
      return final;
    }
  }

  return pollUntilWorkflowReady(refreshState, {
    intervalMs: options.intervalMs,
    maxAttempts: options.maxAttempts,
  });
}
