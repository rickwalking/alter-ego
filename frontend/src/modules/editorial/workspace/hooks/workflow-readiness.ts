/** Readiness checks and polling for editorial workflow state. */

import {
  EDITORIAL_PHASES,
  EDITORIAL_WORKFLOW_RESUME_POLL_INTERVAL_MS,
  EDITORIAL_WORKFLOW_RESUME_POLL_MAX_ATTEMPTS,
} from "@/constants/editorial-workflow";
import { WORKFLOW_PHASE_STATUS } from "@/constants/workflow";
import type { EditorialWorkflowState } from "@/modules/editorial/workspace/types-ai";

function hasContentArtifacts(state: EditorialWorkflowState): boolean {
  const draftCount = state.slide_drafts.length;
  const outlineCount = state.outline.length;
  return draftCount > 0 && (outlineCount === 0 || draftCount >= outlineCount);
}

function hasFinalReviewArtifacts(state: EditorialWorkflowState): boolean {
  return (
    Boolean(state.caption?.trim()) ||
    Boolean(state.blog_markdown?.trim()) ||
    Object.keys(state.rubric_scores ?? {}).length > 0
  );
}

const PHASE_ARTIFACT_CHECKS: Record<
  string,
  (state: EditorialWorkflowState) => boolean
> = {
  [EDITORIAL_PHASES.RESEARCH]: (state) => state.research_findings.length > 0,
  [EDITORIAL_PHASES.OUTLINE]: (state) => state.outline.length > 0,
  [EDITORIAL_PHASES.CONTENT]: hasContentArtifacts,
  [EDITORIAL_PHASES.DESIGN]: (state) => state.design_applied === true,
  [EDITORIAL_PHASES.IMAGES]: (state) => (state.image_assets?.length ?? 0) > 0,
  [EDITORIAL_PHASES.FINAL_REVIEW]: hasFinalReviewArtifacts,
};

export function hasPhaseArtifacts(state: EditorialWorkflowState): boolean {
  const check = Object.hasOwn(PHASE_ARTIFACT_CHECKS, state.current_phase)
    ? PHASE_ARTIFACT_CHECKS[state.current_phase]
    : undefined;
  return check ? check(state) : true;
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

function sleep(ms: number): Promise<void> {
  return new Promise<void>((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

function readyOrNull(
  state: EditorialWorkflowState | null,
): EditorialWorkflowState | null {
  return state && isWorkflowReady(state) ? state : null;
}

interface WorkflowPollOptions {
  intervalMs?: number;
  maxAttempts?: number;
}

async function pollUntilWorkflowReady(
  refreshState: () => Promise<EditorialWorkflowState | null>,
  options?: WorkflowPollOptions,
): Promise<EditorialWorkflowState | null> {
  const intervalMs =
    options?.intervalMs ?? EDITORIAL_WORKFLOW_RESUME_POLL_INTERVAL_MS;
  const maxAttempts =
    options?.maxAttempts ?? EDITORIAL_WORKFLOW_RESUME_POLL_MAX_ATTEMPTS;

  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    const ready = readyOrNull(await refreshState());
    if (ready) {
      return ready;
    }
    await sleep(intervalMs);
  }
  return refreshState();
}

async function waitForSseState(
  getState: () => EditorialWorkflowState | null,
  intervalMs: number,
  maxAttempts: number,
): Promise<EditorialWorkflowState | null> {
  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    const ready = readyOrNull(getState());
    if (ready) {
      return ready;
    }
    await sleep(intervalMs);
  }
  return readyOrNull(getState());
}

export async function waitUntilWorkflowReadyWithTransport(
  getState: () => EditorialWorkflowState | null,
  refreshState: () => Promise<EditorialWorkflowState | null>,
  options: WorkflowPollOptions & { preferSse: boolean },
): Promise<EditorialWorkflowState | null> {
  const intervalMs =
    options.intervalMs ?? EDITORIAL_WORKFLOW_RESUME_POLL_INTERVAL_MS;
  const maxAttempts =
    options.maxAttempts ?? EDITORIAL_WORKFLOW_RESUME_POLL_MAX_ATTEMPTS;

  const sseReady = options.preferSse
    ? await waitForSseState(getState, intervalMs, maxAttempts)
    : null;
  return (
    sseReady ??
    pollUntilWorkflowReady(refreshState, {
      intervalMs: options.intervalMs,
      maxAttempts: options.maxAttempts,
    })
  );
}
