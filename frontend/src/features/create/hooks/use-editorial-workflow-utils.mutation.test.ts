/**
 * Exhaustive mutation-killing tests for editorial workflow utils.
 * Complements use-editorial-workflow-utils.test.ts with branch-level assertions.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { HTTP_STATUS } from "@/constants/api";
import {
  EDITORIAL_PHASES,
  EDITORIAL_WORKFLOW_RESUME_CLIENT_ERROR_STATUSES,
  EDITORIAL_WORKFLOW_SSE_EVENTS,
  EDITORIAL_WORKFLOW_TRANSPORT_MODE,
} from "@/constants/editorial-workflow";
import { WORKFLOW_PHASE_STATUS } from "@/constants/workflow";
import type { EditorialWorkflowState } from "@/features/blog/types-ai";
import {
  appendUniquePhase,
  hasPhaseArtifacts,
  isResumeAcceptedResponse,
  isResumeClientErrorStatus,
  isResumeTransportFailure,
  isWorkflowReady,
  mergeWorkflowState,
  normalizeProgressPayload,
  parseWorkflowEvent,
  readApiError,
  resolveWorkflowEventPayload,
  shouldPollWorkflowState,
  waitUntilWorkflowReadyWithTransport,
} from "./use-editorial-workflow-utils";

const baseState: EditorialWorkflowState = {
  project_id: "project-1",
  current_phase: EDITORIAL_PHASES.RESEARCH,
  phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
  research_findings: [{ title: "Finding" }],
  outline: [{ title: "Intro" }],
  slide_drafts: [{ draft_text: "Body" }],
  image_assets: ["/tmp/slide.jpg"],
  design_applied: true,
  persona_scores: { voice_match: 90 },
  rubric_scores: { clarity: 88 },
  caption: "Caption",
  blog_markdown: "# Blog",
  status: "published",
  lock_version: 2,
};

describe("editorial workflow utils mutation coverage", () => {
  beforeEach(() => {
    vi.useRealTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("merges every full-workflow snapshot field from SSE payloads", () => {
    const merged = mergeWorkflowState("project-1", null, {
      project_id: "project-1",
      current_phase: EDITORIAL_PHASES.FINAL_REVIEW,
      phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
      research_findings: [{ title: "Finding" }],
      outline: [{ title: "Intro" }],
      slide_drafts: [{ draft_text: "Body" }],
      image_assets: ["/assets/slide.png"],
      design_applied: true,
      rubric_scores: { clarity: 95 },
      persona_scores: { voice_match: 91 },
      caption: "Final caption",
      blog_markdown: "# Final",
      status: "published",
      phase_progress: { current: 3, total: 3 },
    });

    expect(merged).toMatchObject({
      project_id: "project-1",
      current_phase: EDITORIAL_PHASES.FINAL_REVIEW,
      image_assets: ["/assets/slide.png"],
      design_applied: true,
      rubric_scores: { clarity: 95 },
      persona_scores: { voice_match: 91 },
      caption: "Final caption",
      blog_markdown: "# Final",
      status: "published",
      phase_progress: { current: 3, total: 3 },
    });
  });

  it("falls back to partial merge when payload is missing required arrays", () => {
    const merged = mergeWorkflowState("project-1", baseState, {
      phase: EDITORIAL_PHASES.OUTLINE,
      phase_status: WORKFLOW_PHASE_STATUS.IN_PROGRESS,
      outline: [{ title: "Updated intro" }],
    });

    expect(merged.current_phase).toBe(EDITORIAL_PHASES.OUTLINE);
    expect(merged.outline).toEqual([{ title: "Updated intro" }]);
    expect(merged.research_findings).toEqual(baseState.research_findings);
    expect(merged.caption).toBe("Caption");
  });

  it("uses projectId when full payload omits project_id", () => {
    const merged = mergeWorkflowState("project-1", null, {
      phase: EDITORIAL_PHASES.RESEARCH,
      phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
      research_findings: [{ title: "Finding" }],
      outline: [],
      slide_drafts: [],
    });

    expect(merged.project_id).toBe("project-1");
  });

  it("preserves defaults for optional full-workflow fields", () => {
    const merged = mergeWorkflowState("project-1", null, {
      project_id: "project-1",
      current_phase: EDITORIAL_PHASES.RESEARCH,
      phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
      research_findings: [{ title: "Finding" }],
      outline: [],
      slide_drafts: [],
    });

    expect(merged.image_assets).toEqual([]);
    expect(merged.design_applied).toBe(false);
    expect(merged.status).toBe("draft");
  });

  it("maps known artifact types and ignores unknown artifact types", () => {
    expect(
      resolveWorkflowEventPayload({
        event: EDITORIAL_WORKFLOW_SSE_EVENTS.ARTIFACT,
        artifact_type: "outline",
        data: [{ title: "Intro" }],
      }).outline,
    ).toEqual([{ title: "Intro" }]);

    expect(
      resolveWorkflowEventPayload({
        event: EDITORIAL_WORKFLOW_SSE_EVENTS.ARTIFACT,
        artifact_type: "unknown",
        data: [{ title: "Ignored" }],
      }).outline,
    ).toBeUndefined();
  });

  it("merges review_required gate payload fields onto the event", () => {
    const resolved = resolveWorkflowEventPayload({
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
    });

    expect(resolved.research_findings).toEqual([{ title: "Finding" }]);
    expect(resolved.phase).toBe("research");
  });

  it("normalizes nested and flat progress payloads", () => {
    expect(
      normalizeProgressPayload({
        phase_progress: { current: 1, total: 4 },
      }),
    ).toEqual({ current: 1, total: 4 });

    expect(
      normalizeProgressPayload({
        event: EDITORIAL_WORKFLOW_SSE_EVENTS.PROGRESS,
        percent: 50,
        message: "Halfway",
        slides: [{ index: 1 }],
      }),
    ).toEqual({
      percent: 50,
      message: "Halfway",
      slides: [{ index: 1 }],
    });

    expect(
      normalizeProgressPayload({
        event: EDITORIAL_WORKFLOW_SSE_EVENTS.PHASE_CHANGED,
        phase: "outline",
      }),
    ).toBeUndefined();
  });

  it("evaluates negative artifact readiness for each editorial phase", () => {
    expect(
      hasPhaseArtifacts({
        ...baseState,
        current_phase: EDITORIAL_PHASES.RESEARCH,
        research_findings: [],
      }),
    ).toBe(false);
    expect(
      hasPhaseArtifacts({
        ...baseState,
        current_phase: EDITORIAL_PHASES.OUTLINE,
        outline: [],
      }),
    ).toBe(false);
    expect(
      hasPhaseArtifacts({
        ...baseState,
        current_phase: EDITORIAL_PHASES.CONTENT,
        outline: [{ title: "Intro" }, { title: "Body" }],
        slide_drafts: [{ draft_text: "Only one" }],
      }),
    ).toBe(false);
    expect(
      hasPhaseArtifacts({
        ...baseState,
        current_phase: EDITORIAL_PHASES.DESIGN,
        design_applied: false,
      }),
    ).toBe(false);
    expect(
      hasPhaseArtifacts({
        ...baseState,
        current_phase: EDITORIAL_PHASES.IMAGES,
        image_assets: [],
      }),
    ).toBe(false);
    expect(
      hasPhaseArtifacts({
        ...baseState,
        current_phase: EDITORIAL_PHASES.FINAL_REVIEW,
        caption: "   ",
        blog_markdown: "",
        rubric_scores: {},
      }),
    ).toBe(false);
  });

  it("treats in-progress workflow states as not ready", () => {
    expect(
      isWorkflowReady({
        ...baseState,
        phase_status: WORKFLOW_PHASE_STATUS.IN_PROGRESS,
      }),
    ).toBe(false);
  });

  it("classifies every resume client error status", () => {
    for (const status of EDITORIAL_WORKFLOW_RESUME_CLIENT_ERROR_STATUSES) {
      expect(isResumeClientErrorStatus(status)).toBe(true);
    }
    expect(isResumeClientErrorStatus(HTTP_STATUS.NOT_FOUND)).toBe(false);
  });

  it("classifies every resume transport failure status", () => {
    expect(isResumeTransportFailure(HTTP_STATUS.INTERNAL_SERVER_ERROR)).toBe(true);
    expect(isResumeTransportFailure(HTTP_STATUS.BAD_GATEWAY)).toBe(true);
    expect(isResumeTransportFailure(HTTP_STATUS.SERVICE_UNAVAILABLE)).toBe(true);
    expect(isResumeTransportFailure(HTTP_STATUS.GATEWAY_TIMEOUT)).toBe(true);
    expect(isResumeTransportFailure(HTTP_STATUS.OK)).toBe(false);
  });

  it("rejects resume accepted payloads missing required fields", () => {
    expect(
      isResumeAcceptedResponse({
        accepted: true,
        project_id: "project-1",
        current_phase: "research",
        phase_status: WORKFLOW_PHASE_STATUS.IN_PROGRESS,
        lock_version: "2",
      }),
    ).toBe(false);
  });

  it("returns the last refresh result when polling never becomes ready", async () => {
    vi.useFakeTimers();
    const notReady: EditorialWorkflowState = {
      ...baseState,
      phase_status: WORKFLOW_PHASE_STATUS.IN_PROGRESS,
      research_findings: [],
    };

    const refreshState = vi.fn(async () => notReady);
    const waitPromise = waitUntilWorkflowReadyWithTransport(
      () => null,
      refreshState,
      { preferSse: false, intervalMs: 5, maxAttempts: 1 },
    );

    await vi.advanceTimersByTimeAsync(20);
    await expect(waitPromise).resolves.toBe(notReady);
    expect(refreshState).toHaveBeenCalledTimes(2);
    vi.useRealTimers();
  });

  it("does not poll when transport mode is not fallback", () => {
    expect(
      shouldPollWorkflowState(
        WORKFLOW_PHASE_STATUS.IN_PROGRESS,
        EDITORIAL_WORKFLOW_TRANSPORT_MODE.SSE,
        EDITORIAL_WORKFLOW_TRANSPORT_MODE.POLLING_FALLBACK,
      ),
    ).toBe(false);
  });

  it("reads API errors and preserves fallback behavior", async () => {
    await expect(
      readApiError(
        { json: async () => ({ detail: "conflict" }) } as Response,
        "fallback",
      ),
    ).resolves.toBe("conflict");

    await expect(
      readApiError(
        {
          json: async () => ({
            detail: [{ msg: "invalid" }, { msg: "missing" }],
          }),
        } as Response,
        "fallback",
      ),
    ).resolves.toBe("invalid, missing");

    await expect(
      readApiError({ json: async () => ({}) } as Response, "fallback"),
    ).resolves.toBe("fallback");
  });

  it("parses workflow JSON events safely", () => {
    expect(parseWorkflowEvent('{"phase":"research"}')).toEqual({ phase: "research" });
    expect(parseWorkflowEvent("not-json")).toBeNull();
  });

  it("appends unique phases only once", () => {
    expect(appendUniquePhase(["research"], "outline")).toEqual([
      "research",
      "outline",
    ]);
    expect(appendUniquePhase(["research"], "")).toEqual(["research"]);
  });

  it("uses partial merge when project_id does not match", () => {
    const merged = mergeWorkflowState("project-1", baseState, {
      project_id: "other-project",
      current_phase: "outline",
      phase_status: WORKFLOW_PHASE_STATUS.IN_PROGRESS,
      research_findings: [],
      outline: [{ title: "Updated" }],
      slide_drafts: [],
    });

    expect(merged.project_id).toBe("project-1");
    expect(merged.outline).toEqual([{ title: "Updated" }]);
  });

  it("merges each optional partial field independently", () => {
    const previous: EditorialWorkflowState = {
      ...baseState,
      image_assets: ["/prev.jpg"],
      design_applied: false,
      phase_progress: { current: 1, total: 2 },
      rubric_scores: { clarity: 80 },
      persona_scores: { voice_match: 70 },
      caption: "Previous",
      blog_markdown: "# Previous",
      status: "draft",
    };

    const merged = mergeWorkflowState("project-1", previous, {
      image_assets: ["/next.jpg"],
      design_applied: true,
      phase_progress: { current: 2, total: 2 },
      rubric_scores: { clarity: 95 },
      persona_scores: { voice_match: 91 },
      caption: "Next caption",
      blog_markdown: "# Next",
      status: "published",
      current_phase: "content",
      phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
    });

    expect(merged.image_assets).toEqual(["/next.jpg"]);
    expect(merged.design_applied).toBe(true);
    expect(merged.phase_progress).toEqual({ current: 2, total: 2 });
    expect(merged.rubric_scores).toEqual({ clarity: 95 });
    expect(merged.persona_scores).toEqual({ voice_match: 91 });
    expect(merged.caption).toBe("Next caption");
    expect(merged.blog_markdown).toBe("# Next");
    expect(merged.status).toBe("published");
    expect(merged.current_phase).toBe("content");
  });

  it("prefers payload phase aliases during partial merge", () => {
    const merged = mergeWorkflowState("project-1", baseState, {
      phase: "images",
      current_phase: "ignored",
    });

    expect(merged.current_phase).toBe("images");
  });

  it("accepts content phase readiness when drafts exist without outline", () => {
    expect(
      hasPhaseArtifacts({
        ...baseState,
        current_phase: EDITORIAL_PHASES.CONTENT,
        outline: [],
        slide_drafts: [{ draft_text: "Slide 1" }],
      }),
    ).toBe(true);
  });

  it("accepts content phase readiness when drafts cover the outline", () => {
    expect(
      hasPhaseArtifacts({
        ...baseState,
        current_phase: EDITORIAL_PHASES.CONTENT,
        outline: [{ title: "Intro" }, { title: "Body" }],
        slide_drafts: [{ draft_text: "Intro" }, { draft_text: "Body" }],
      }),
    ).toBe(true);
  });

  it("rejects resume accepted payloads missing each required field", () => {
    const valid = {
      accepted: true,
      project_id: "project-1",
      current_phase: "research",
      phase_status: WORKFLOW_PHASE_STATUS.IN_PROGRESS,
      lock_version: 2,
    };

    expect(isResumeAcceptedResponse(valid)).toBe(true);
    expect(isResumeAcceptedResponse({ ...valid, accepted: false })).toBe(false);
    expect(isResumeAcceptedResponse({ ...valid, project_id: 1 })).toBe(false);
    expect(isResumeAcceptedResponse({ ...valid, current_phase: 1 })).toBe(false);
    expect(isResumeAcceptedResponse({ ...valid, phase_status: 1 })).toBe(false);
    expect(isResumeAcceptedResponse({ ...valid, lock_version: "2" })).toBe(false);
  });

  it("returns early from polling when refresh becomes ready on first attempt", async () => {
    vi.useFakeTimers();
    const refreshState = vi.fn(async () => ({
      ...baseState,
      phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
      research_findings: [{ title: "Finding" }],
    }));

    const waitPromise = waitUntilWorkflowReadyWithTransport(
      () => null,
      refreshState,
      { preferSse: false, intervalMs: 100, maxAttempts: 5 },
    );

    await expect(waitPromise).resolves.toMatchObject({
      research_findings: [{ title: "Finding" }],
    });
    expect(refreshState).toHaveBeenCalledTimes(1);
    vi.useRealTimers();
  });

  it("returns gate phase values from nested review payloads", () => {
    const resolved = resolveWorkflowEventPayload({
      event: EDITORIAL_WORKFLOW_SSE_EVENTS.REVIEW_REQUIRED,
      gate_payload: {
        current_phase: "outline",
        phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
      },
    });

    expect(resolved.phase).toBe("outline");
    expect(resolved.phase_status).toBe(WORKFLOW_PHASE_STATUS.AWAITING_HUMAN);
  });

  it("keeps original payload when artifact data is missing", () => {
    const payload = resolveWorkflowEventPayload({
      event: EDITORIAL_WORKFLOW_SSE_EVENTS.ARTIFACT,
      artifact_type: "outline",
    });

    expect(payload.outline).toBeUndefined();
  });
});
