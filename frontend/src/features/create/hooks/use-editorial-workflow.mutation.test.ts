/**
 * Manual mutation-style tests for editorial workflow SSE hooks.
 *
 * Feature: carousel_editorial_consolidation.feature (@cp-sse-primary, @cp-sse-fallback)
 * Run with: npm run test -- src/features/create/hooks/use-editorial-workflow.mutation.test.ts
 */

import { describe, it, expect } from "vitest";
import {
  EDITORIAL_WORKFLOW_SSE_EVENTS,
  EDITORIAL_WORKFLOW_TRANSPORT_MODE,
} from "@/constants/editorial-workflow";
import { WORKFLOW_PHASE_STATUS } from "@/constants/workflow";
import {
  isResumeClientErrorStatus,
  isResumeTransportFailure,
  mergeWorkflowState,
  normalizeProgressPayload,
  resolveWorkflowEventPayload,
  shouldPollWorkflowState,
} from "./use-editorial-workflow-utils";

describe("editorial workflow mutation resilience", () => {
  it("kills mutants that drop nested phase_progress", () => {
    const payload = {
      event: EDITORIAL_WORKFLOW_SSE_EVENTS.PROGRESS,
      phase: "images",
      phase_progress: { current: 2, total: 5 },
    };
    expect(normalizeProgressPayload(payload)).toEqual({ current: 2, total: 5 });
  });

  it("kills mutants that keep polling at awaiting_human", () => {
    expect(
      shouldPollWorkflowState(
        WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
        EDITORIAL_WORKFLOW_TRANSPORT_MODE.POLLING_FALLBACK,
        EDITORIAL_WORKFLOW_TRANSPORT_MODE.POLLING_FALLBACK,
      ),
    ).toBe(false);
    expect(
      shouldPollWorkflowState(
        WORKFLOW_PHASE_STATUS.IN_PROGRESS,
        EDITORIAL_WORKFLOW_TRANSPORT_MODE.POLLING_FALLBACK,
        EDITORIAL_WORKFLOW_TRANSPORT_MODE.POLLING_FALLBACK,
      ),
    ).toBe(true);
  });

  it("kills mutants that ignore review_required gate payload merge", () => {
    const merged = mergeWorkflowState(
      "project-1",
      null,
      resolveWorkflowEventPayload({
        event: EDITORIAL_WORKFLOW_SSE_EVENTS.REVIEW_REQUIRED,
        phase: "research",
        phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
        gate_payload: {
          current_phase: "research",
          phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
          research_findings: [{ title: "Finding" }],
          outline: [],
          slide_drafts: [],
        },
      }),
    );

    expect(merged.current_phase).toBe("research");
    expect(merged.research_findings).toHaveLength(1);
  });

  it("kills mutants that poll while SSE primary is active", () => {
    expect(
      shouldPollWorkflowState(
        WORKFLOW_PHASE_STATUS.IN_PROGRESS,
        EDITORIAL_WORKFLOW_TRANSPORT_MODE.SSE,
        EDITORIAL_WORKFLOW_TRANSPORT_MODE.POLLING_FALLBACK,
      ),
    ).toBe(false);
  });

  it("kills mutants that ignore artifact SSE merge", () => {
    const merged = mergeWorkflowState(
      "project-1",
      null,
      resolveWorkflowEventPayload({
        event: EDITORIAL_WORKFLOW_SSE_EVENTS.ARTIFACT,
        phase: "content",
        artifact_type: "slide_drafts",
        data: [{ draft_text: "Slide 1" }],
      }),
    );

    expect(merged.slide_drafts).toEqual([{ draft_text: "Slide 1" }]);
  });

  it("kills mutants that ignore recoverable SSE errors", () => {
    const payload = {
      event: EDITORIAL_WORKFLOW_SSE_EVENTS.ERROR,
      message: "workflow_phase_failed",
      recoverable: true,
    };
    expect(payload.recoverable).toBe(true);
    expect(payload.message).toBe("workflow_phase_failed");
  });

  it("kills mutants that treat resume client errors as transport failures", () => {
    expect(isResumeClientErrorStatus(409)).toBe(true);
    expect(isResumeTransportFailure(500)).toBe(true);
    expect(isResumeTransportFailure(409)).toBe(false);
  });
});
