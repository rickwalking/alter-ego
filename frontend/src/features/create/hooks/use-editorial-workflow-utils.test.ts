import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { EDITORIAL_PHASES, EDITORIAL_WORKFLOW_SSE_EVENTS } from "@/constants/editorial-workflow";
import { HTTP_STATUS } from "@/constants/api";
import { WORKFLOW_PHASE_STATUS } from "@/constants/workflow";
import type { EditorialWorkflowState } from "@/features/blog/types-ai";
import {
  hasPhaseArtifacts,
  isResumeClientErrorStatus,
  isResumeAcceptedResponse,
  isResumeTransportFailure,
  isWorkflowReady,
  mergeWorkflowState,
  normalizeProgressPayload,
  resolveWorkflowEventPayload,
  waitUntilWorkflowReadyWithTransport,
} from "./use-editorial-workflow-utils";

describe("useEditorialWorkflow utils", () => {
  // Feature: Unified workflow progress in create workspace
  // Scenario: SSE progress merges nested phase_progress into client state
  it("merges nested phase_progress from SSE progress events", () => {
    const payload = {
      event: EDITORIAL_WORKFLOW_SSE_EVENTS.PROGRESS,
      project_id: "project-1",
      phase: "images",
      phase_progress: {
        current: 4,
        total: 10,
        label: "Generating slide 4 of 10",
      },
    };

    const merged = mergeWorkflowState("project-1", null, payload);

    expect(merged.phase_progress).toEqual({
      current: 4,
      total: 10,
      label: "Generating slide 4 of 10",
    });
  });

  it("normalizes legacy flat progress fields into phase_progress", () => {
    const normalized = normalizeProgressPayload({
      event: EDITORIAL_WORKFLOW_SSE_EVENTS.PROGRESS,
      phase: "images",
      current: 2,
      total: 5,
      label: "Generating slide 2 of 5",
    });

    expect(normalized).toEqual({
      current: 2,
      total: 5,
      label: "Generating slide 2 of 5",
    });
  });

  it("merges artifact SSE payloads into workflow state fields", () => {
    const payload = resolveWorkflowEventPayload({
      event: EDITORIAL_WORKFLOW_SSE_EVENTS.ARTIFACT,
      project_id: "project-1",
      phase: "outline",
      artifact_type: "outline",
      data: [{ title: "Intro" }],
    });

    const merged = mergeWorkflowState("project-1", null, payload);

    expect(merged.outline).toEqual([{ title: "Intro" }]);
    expect(merged.current_phase).toBe("outline");
  });

  it("classifies resume client errors separately from transport failures", () => {
    expect(isResumeClientErrorStatus(HTTP_STATUS.CONFLICT)).toBe(true);
    expect(isResumeTransportFailure(HTTP_STATUS.INTERNAL_SERVER_ERROR)).toBe(true);
    expect(isResumeTransportFailure(HTTP_STATUS.CONFLICT)).toBe(false);
  });

  it("validates async resume accepted payloads", () => {
    expect(
      isResumeAcceptedResponse({
        accepted: true,
        project_id: "project-1",
        current_phase: "research",
        phase_status: WORKFLOW_PHASE_STATUS.IN_PROGRESS,
        lock_version: 2,
      }),
    ).toBe(true);
  });

  // Feature: Resume recovery without false errors or manual refresh
  // Scenario: Polling recovery waits for artifacts not only gate status
  it("requires artifacts before workflow is ready at human gate", () => {
    const emptyOutlineGate = {
      project_id: "project-1",
      current_phase: "outline",
      phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
      research_findings: [],
      outline: [],
      slide_drafts: [],
      status: "draft",
    };
    expect(isWorkflowReady(emptyOutlineGate)).toBe(false);
    expect(
      hasPhaseArtifacts({
        ...emptyOutlineGate,
        outline: [{ title: "Intro" }],
      }),
    ).toBe(true);
  });

  it("evaluates hasPhaseArtifacts for each editorial phase", () => {
    const base: EditorialWorkflowState = {
      project_id: "project-1",
      current_phase: EDITORIAL_PHASES.RESEARCH,
      phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
      research_findings: [],
      outline: [],
      slide_drafts: [],
      status: "draft",
    };

    expect(hasPhaseArtifacts({ ...base, research_findings: [{ title: "Finding" }] })).toBe(
      true,
    );
    expect(
      hasPhaseArtifacts({
        ...base,
        current_phase: EDITORIAL_PHASES.OUTLINE,
        outline: [{ title: "Intro" }],
      }),
    ).toBe(true);
    expect(
      hasPhaseArtifacts({
        ...base,
        current_phase: EDITORIAL_PHASES.CONTENT,
        outline: [{ title: "Intro" }, { title: "Body" }],
        slide_drafts: [{ slide_index: 1 }],
      }),
    ).toBe(false);
    expect(
      hasPhaseArtifacts({
        ...base,
        current_phase: EDITORIAL_PHASES.CONTENT,
        outline: [{ title: "Intro" }],
        slide_drafts: [{ slide_index: 1 }],
      }),
    ).toBe(true);
    expect(
      hasPhaseArtifacts({
        ...base,
        current_phase: EDITORIAL_PHASES.DESIGN,
        design_applied: true,
      }),
    ).toBe(true);
    expect(
      hasPhaseArtifacts({
        ...base,
        current_phase: EDITORIAL_PHASES.IMAGES,
        image_assets: ["/tmp/slide.jpg"],
      }),
    ).toBe(true);
    expect(
      hasPhaseArtifacts({
        ...base,
        current_phase: EDITORIAL_PHASES.FINAL_REVIEW,
        caption: "Ready caption",
      }),
    ).toBe(true);
  });

  it("waits on in-memory SSE state before falling back to polling refresh", async () => {
    vi.useFakeTimers();
    const refreshState = vi.fn(async () => null);
    let current: EditorialWorkflowState | null = {
      project_id: "project-1",
      current_phase: "research",
      phase_status: WORKFLOW_PHASE_STATUS.IN_PROGRESS,
      research_findings: [],
      outline: [],
      slide_drafts: [],
      status: "draft",
    };

    const waitPromise = waitUntilWorkflowReadyWithTransport(
      () => current,
      refreshState,
      { preferSse: true, intervalMs: 100, maxAttempts: 5 },
    );

    await vi.advanceTimersByTimeAsync(250);
    current = {
      ...current,
      current_phase: "outline",
      phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
      outline: [{ title: "Intro" }],
    };
    await vi.advanceTimersByTimeAsync(100);

    await expect(waitPromise).resolves.toEqual(current);
    expect(refreshState).not.toHaveBeenCalled();
    vi.useRealTimers();
  });
});
