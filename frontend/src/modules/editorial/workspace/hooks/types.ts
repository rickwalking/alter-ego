/**
 * Editorial workspace hook data-shape types (colocated `types.ts`).
 *
 * Per the component-type-location convention (AE-0144,
 * `frontend/scripts/component-type-location.config.mjs`), object-shape types
 * live here rather than inline in the hook `.ts` files.
 */

import type { Dispatch, RefObject, SetStateAction } from "react";
import type { EditorialWorkflowTransportMode } from "@/constants/editorial-workflow";
import type {
  EditorialWorkflowState,
  LocalizedSlideReview,
} from "@/modules/editorial/workspace/types-ai";

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

export interface EditorialWorkflowResumeAcceptedResponse {
  accepted: boolean;
  project_id: string;
  current_phase: string;
  phase_status: string;
  lock_version: number;
}

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
  // AE-0315 run lifecycle payload fields (run.started / run.stage_changed /
  // run.finished).
  run_started_at?: string | null;
  run_stage?: string | null;
  reason?: string;
}

export interface StartWorkflowInput {
  topic: string;
  audience: string;
  brief: string;
  sources: Array<{ title: string; content: string; source_type?: string }>;
  personaId?: string;
}
