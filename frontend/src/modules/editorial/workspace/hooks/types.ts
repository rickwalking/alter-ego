/**
 * Editorial workspace hook data-shape types (colocated `types.ts`).
 *
 * Per the component-type-location convention (AE-0144,
 * `frontend/scripts/component-type-location.config.mjs`), object-shape types
 * live here rather than inline in the hook `.ts` files.
 */

import type {
  Dispatch,
  MutableRefObject,
  RefObject,
  SetStateAction,
} from "react";
import type {
  EditorialWorkflowTransportMode,
  WorkflowStreamProbeOutcome,
} from "@/constants/editorial-workflow";
import type {
  EditorialWorkflowState,
  LocalizedSlideReview,
  SlideValidationViolation,
} from "@/modules/editorial/workspace/types-ai";
import type { SlideFieldErrors } from "@/modules/editorial/workspace/lib/slide-field-errors";

export interface EditorialReviseOptions {
  targetPhase?: string;
  editedText?: string;
  editedLocalizedSlides?: LocalizedSlideReview[];
}

export interface UseEditorialWorkflowResumeParams {
  projectId: string;
  lockVersion: number | undefined;
  translateError: (key: string) => string;
  workflowStateRef: RefObject<EditorialWorkflowState | null>;
  transportModeRef: RefObject<EditorialWorkflowTransportMode | null>;
  refreshState: () => Promise<EditorialWorkflowState | null>;
  setState: Dispatch<SetStateAction<EditorialWorkflowState | null>>;
  setPhaseEvents: Dispatch<SetStateAction<string[]>>;
  setLoading: Dispatch<SetStateAction<boolean>>;
  setError: Dispatch<SetStateAction<string | null>>;
  enterPollingFallback: () => void;
  stopPollingFallback: () => void;
}

export interface UseEditorialWorkflowSseParams {
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

/** AE-0440: the verdict of the auth probe that follows a stream error. */
export interface WorkflowStreamProbeResult {
  outcome: WorkflowStreamProbeOutcome;
  /** The refetched workflow state, present only when `outcome` is OK. */
  state?: EditorialWorkflowState;
}

export interface UseWorkflowStreamReconnectParams {
  projectId: string;
  /** Opens a fresh stream (set by the SSE effect on every run). */
  connectRef: RefObject<(() => void) | null>;
  /** The live stream, or null while waiting to reconnect / disconnected. */
  sourceRef: RefObject<EventSource | null>;
  applyProbedState: (state: EditorialWorkflowState) => void;
  refreshState: () => Promise<EditorialWorkflowState | null>;
  enterPollingFallback: () => void;
  markDisconnected: () => void;
}

export interface WorkflowStreamReconnectApi {
  /** Stream onerror: probe auth, then reconnect with backoff or give up. */
  handleStreamError: () => void;
  /** Stream onopen: reset the budget; a reconnect refetches the state. */
  handleStreamOpen: () => void;
  /** Reopen at once with a fresh budget (retry button, tab regain). */
  reconnectNow: () => void;
  /** Drop pending reconnects and in-flight probes (unmount, disable). */
  cancelReconnect: () => void;
}

export interface EditorialWorkflowResumeAcceptedResponse {
  accepted: boolean;
  project_id: string;
  current_phase: string;
  phase_status: string;
  lock_version: number;
}

export interface WorkflowEventPayload {
  event?: string;
  /** AE-0447: the CAS version a full-state snapshot carries. */
  lock_version?: number;
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
  // AE-0315 run lifecycle payload fields (run.started / run.stage_changed /
  // run.finished).
  run_started_at?: string | null;
  run_stage?: string | null;
  reason?: string;
}

/** AE-0415: options of `useEditorialWorkflow`. */
export interface UseEditorialWorkflowOptions {
  /** Fetch workflow/state on mount (default true; false for a fresh project). */
  initialFetch?: boolean;
}

/** AE-0415 (B27): the review action that started a run, and its phase. */
export interface RecordedResume {
  action: string;
  phase: string;
}

export interface StartWorkflowInput {
  topic: string;
  audience: string;
  brief: string;
  sources: Array<{ title: string; content: string; source_type?: string }>;
  personaId?: string;
}

/** AE-0375: the owner's slide-1 hook for one carousel. */
export interface SaveHookInput {
  projectId: string;
  hookText: string;
}

/** AE-0376: one photo upload to the creator library. */
export interface UploadCreatorPhotoInput {
  file: File;
  role: string;
}

/** AE-0403: the per-field error state of a slide review form. */
export interface SlideFieldErrorState {
  /** Blocking violations still open (edited fields drop out). */
  open: SlideValidationViolation[];
  fieldErrors: SlideFieldErrors;
  slideIndexes: number[];
  /** Drop a field's errors as soon as that field is edited. */
  clearField: (key: string) => void;
}

/** The reconnect backoff timer (AE-0446: split out of the reconnect hook). */
export interface ReconnectTimer {
  attemptsRef: MutableRefObject<number>;
  clearTimer: () => void;
  scheduleReconnect: () => void;
}

/** What reviving the stream on tab focus needs (AE-0446). */
export interface ResumeOnVisibleDeps extends Pick<
  UseWorkflowStreamReconnectParams,
  "connectRef" | "sourceRef" | "refreshState"
> {
  probeThen: (onReopenable: () => void) => void;
  reconnectNow: () => void;
}

/** What starting a workflow needs (AE-0446: split out of the main hook). */
export type StartWorkflowDeps = Pick<
  UseEditorialWorkflowResumeParams,
  | "projectId"
  | "translateError"
  | "workflowStateRef"
  | "refreshState"
  | "setState"
  | "setPhaseEvents"
  | "setLoading"
  | "setError"
>;

/** ``useEditorialWorkflow``'s own state + refresh (AE-0446). */
export interface WorkflowCore {
  state: EditorialWorkflowState | null;
  setState: Dispatch<SetStateAction<EditorialWorkflowState | null>>;
  phaseEvents: string[];
  setPhaseEvents: Dispatch<SetStateAction<string[]>>;
  loading: boolean;
  setLoading: Dispatch<SetStateAction<boolean>>;
  error: string | null;
  setError: Dispatch<SetStateAction<string | null>>;
  transportMode: EditorialWorkflowTransportMode;
  setTransportMode: Dispatch<SetStateAction<EditorialWorkflowTransportMode>>;
  refreshState: () => Promise<EditorialWorkflowState | null>;
}
