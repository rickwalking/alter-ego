import { describe, it, expect, vi } from "vitest";
import {
  EDITORIAL_PHASES,
  EDITORIAL_WORKFLOW_SSE_EVENTS,
  EDITORIAL_WORKFLOW_TRANSPORT_MODE,
} from "@/constants/editorial-workflow";
import { HTTP_STATUS } from "@/constants/api";
import { WORKFLOW_PHASE_STATUS } from "@/constants/workflow";
import type { EditorialWorkflowState } from "@/features/blog/types-ai";
import {
  appendUniquePhase,
  hasPhaseArtifacts,
  isResumeClientErrorStatus,
  isResumeAcceptedResponse,
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
    expect(isResumeTransportFailure(HTTP_STATUS.INTERNAL_SERVER_ERROR)).toBe(
      true,
    );
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

    expect(
      hasPhaseArtifacts({ ...base, research_findings: [{ title: "Finding" }] }),
    ).toBe(true);
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

  it("reads string and array validation errors from API responses", async () => {
    await expect(
      readApiError(
        {
          json: async () => ({ detail: "version_conflict" }),
        } as Response,
        "fallback",
      ),
    ).resolves.toBe("version_conflict");

    await expect(
      readApiError(
        {
          json: async () => ({
            detail: [{ msg: "field required" }, { msg: "invalid action" }],
          }),
        } as Response,
        "fallback",
      ),
    ).resolves.toBe("field required, invalid action");

    await expect(
      readApiError({ json: async () => ({}) } as Response, "fallback"),
    ).resolves.toBe("fallback");
  });

  it("returns fallback when error payloads are malformed", async () => {
    await expect(
      readApiError(
        {
          json: async () => {
            throw new Error("invalid json");
          },
        } as unknown as Response,
        "resume failed",
      ),
    ).resolves.toBe("resume failed");
  });

  it("appends unique phases and ignores empty duplicates", () => {
    expect(appendUniquePhase(["research"], "outline")).toEqual([
      "research",
      "outline",
    ]);
    expect(appendUniquePhase(["research"], "research")).toEqual(["research"]);
    expect(appendUniquePhase(["research"], undefined)).toEqual(["research"]);
  });

  it("returns null for invalid workflow SSE payloads", () => {
    expect(parseWorkflowEvent("{not-json")).toBeNull();
    expect(parseWorkflowEvent('{"event":"progress"}')).toEqual({
      event: "progress",
    });
  });

  it("treats failed and rejected workflow states as ready", () => {
    const base = {
      project_id: "project-1",
      current_phase: "research",
      phase_status: WORKFLOW_PHASE_STATUS.FAILED,
      research_findings: [],
      outline: [],
      slide_drafts: [],
      status: "draft",
    };
    expect(isWorkflowReady(base)).toBe(true);
    expect(
      isWorkflowReady({
        ...base,
        phase_status: WORKFLOW_PHASE_STATUS.REJECTED,
      }),
    ).toBe(true);
    expect(
      isWorkflowReady({
        ...base,
        phase_status: WORKFLOW_PHASE_STATUS.IN_PROGRESS,
      }),
    ).toBe(false);
  });

  it("rejects malformed async resume acceptance payloads", () => {
    expect(isResumeAcceptedResponse(null)).toBe(false);
    expect(isResumeAcceptedResponse({ accepted: false })).toBe(false);
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

  it("classifies gateway transport failures", () => {
    expect(isResumeTransportFailure(HTTP_STATUS.BAD_GATEWAY)).toBe(true);
    expect(isResumeTransportFailure(HTTP_STATUS.SERVICE_UNAVAILABLE)).toBe(
      true,
    );
    expect(isResumeTransportFailure(HTTP_STATUS.GATEWAY_TIMEOUT)).toBe(true);
    expect(isResumeClientErrorStatus(HTTP_STATUS.BAD_REQUEST)).toBe(true);
  });

  it("falls back to refresh polling when SSE preference is disabled", async () => {
    vi.useFakeTimers();
    const refreshState = vi.fn(async () => ({
      project_id: "project-1",
      current_phase: "outline",
      phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
      research_findings: [],
      outline: [{ title: "Intro" }],
      slide_drafts: [],
      status: "draft",
    }));

    const waitPromise = waitUntilWorkflowReadyWithTransport(
      () => null,
      refreshState,
      { preferSse: false, intervalMs: 10, maxAttempts: 2 },
    );

    await vi.advanceTimersByTimeAsync(20);
    await expect(waitPromise).resolves.toMatchObject({
      current_phase: "outline",
    });
    expect(refreshState).toHaveBeenCalled();
    vi.useRealTimers();
  });

  it("merges partial workflow payloads without full state markers", () => {
    const previous: EditorialWorkflowState = {
      project_id: "project-1",
      current_phase: "research",
      phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
      research_findings: [{ title: "Finding" }],
      outline: [],
      slide_drafts: [],
      image_assets: ["/tmp/image.jpg"],
      design_applied: true,
      caption: "Draft caption",
      status: "draft",
    };

    const merged = mergeWorkflowState("project-1", previous, {
      phase: "outline",
      phase_status: WORKFLOW_PHASE_STATUS.IN_PROGRESS,
      outline: [{ title: "Intro" }],
    });

    expect(merged.current_phase).toBe("outline");
    expect(merged.research_findings).toHaveLength(1);
    expect(merged.image_assets).toEqual(["/tmp/image.jpg"]);
    expect(merged.caption).toBe("Draft caption");
  });

  it("normalizes flat progress fields without nested phase_progress", () => {
    expect(
      normalizeProgressPayload({
        current: 1,
        total: 4,
        label: "Generating slide 1 of 4",
      }),
    ).toEqual({
      current: 1,
      total: 4,
      label: "Generating slide 1 of 4",
    });
  });

  it("returns original payload when review gate payload is absent", () => {
    const payload = {
      event: EDITORIAL_WORKFLOW_SSE_EVENTS.PHASE_CHANGED,
      phase: "outline",
    };
    expect(resolveWorkflowEventPayload(payload)).toEqual(payload);
  });

  it("allows polling only in polling fallback mode and not at human gates", () => {
    expect(
      shouldPollWorkflowState(
        WORKFLOW_PHASE_STATUS.IN_PROGRESS,
        EDITORIAL_WORKFLOW_TRANSPORT_MODE.POLLING_FALLBACK,
        EDITORIAL_WORKFLOW_TRANSPORT_MODE.POLLING_FALLBACK,
      ),
    ).toBe(true);
    expect(
      shouldPollWorkflowState(
        WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
        EDITORIAL_WORKFLOW_TRANSPORT_MODE.POLLING_FALLBACK,
        EDITORIAL_WORKFLOW_TRANSPORT_MODE.POLLING_FALLBACK,
      ),
    ).toBe(false);
  });

  it("treats unknown phases as artifact-ready by default", () => {
    expect(
      hasPhaseArtifacts({
        project_id: "project-1",
        current_phase: "unknown_phase",
        phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
        research_findings: [],
        outline: [],
        slide_drafts: [],
        status: "draft",
      }),
    ).toBe(true);
  });

  it("merges full workflow snapshots from SSE payloads", () => {
    const merged = mergeWorkflowState("project-1", null, {
      project_id: "project-1",
      current_phase: "content",
      phase: "content",
      phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
      research_findings: [{ title: "Finding" }],
      outline: [{ title: "Intro" }],
      slide_drafts: [{ draft_text: "Body" }],
      image_assets: ["/tmp/slide.jpg"],
      design_applied: true,
      caption: "Caption",
      blog_markdown: "# Blog",
      status: "draft",
    });

    expect(merged.current_phase).toBe("content");
    expect(merged.image_assets).toEqual(["/tmp/slide.jpg"]);
    expect(merged.caption).toBe("Caption");
  });

  it("merges distribution fields and workflow_status from partial SSE payloads", () => {
    const previous: EditorialWorkflowState = {
      project_id: "project-1",
      current_phase: "final_review",
      phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
      research_findings: [],
      outline: [],
      slide_drafts: [],
      caption: "Old caption",
      status: "draft",
    };

    const merged = mergeWorkflowState("project-1", previous, {
      linkedin_post_pt: "Post PT",
      linkedin_post_en: "Post EN",
      workflow_status: "approved_for_publish",
    });

    expect(merged.linkedin_post_pt).toBe("Post PT");
    expect(merged.linkedin_post_en).toBe("Post EN");
    expect(merged.workflow_status).toBe("approved_for_publish");
    expect(merged.caption).toBe("Old caption");
  });

  it("preserves previous workflow values when SSE payload is partial", () => {
    const previous: EditorialWorkflowState = {
      project_id: "project-1",
      current_phase: "research",
      phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
      research_findings: [{ title: "Finding" }],
      outline: [{ title: "Intro" }],
      slide_drafts: [],
      persona_scores: { voice_match: 92 },
      status: "draft",
    };

    const merged = mergeWorkflowState("project-1", previous, {
      phase_status: WORKFLOW_PHASE_STATUS.IN_PROGRESS,
    });

    expect(merged.current_phase).toBe("research");
    expect(merged.persona_scores).toEqual({ voice_match: 92 });
    expect(merged.phase_status).toBe(WORKFLOW_PHASE_STATUS.IN_PROGRESS);
  });

  it("maps artifact payloads onto workflow fields", () => {
    const payload = resolveWorkflowEventPayload({
      event: EDITORIAL_WORKFLOW_SSE_EVENTS.ARTIFACT,
      artifact_type: "slide_drafts",
      data: [{ draft_text: "Slide 1" }],
    });

    expect(payload.slide_drafts).toEqual([{ draft_text: "Slide 1" }]);
  });

  it("returns validation detail arrays without messages as fallback", async () => {
    await expect(
      readApiError(
        {
          json: async () => ({ detail: [{ msg: "" }] }),
        } as Response,
        "fallback",
      ),
    ).resolves.toBe("fallback");
  });

  it("polls until refresh returns a ready workflow state", async () => {
    vi.useFakeTimers();
    let attempts = 0;
    const refreshState = vi.fn(async () => {
      attempts += 1;
      if (attempts < 2) {
        return {
          project_id: "project-1",
          current_phase: "outline",
          phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
          research_findings: [],
          outline: [],
          slide_drafts: [],
          status: "draft",
        };
      }
      return {
        project_id: "project-1",
        current_phase: "outline",
        phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
        research_findings: [],
        outline: [{ title: "Intro" }],
        slide_drafts: [],
        status: "draft",
      };
    });

    const waitPromise = waitUntilWorkflowReadyWithTransport(
      () => null,
      refreshState,
      { preferSse: false, intervalMs: 10, maxAttempts: 3 },
    );

    await vi.advanceTimersByTimeAsync(30);
    await expect(waitPromise).resolves.toMatchObject({
      outline: [{ title: "Intro" }],
    });
    vi.useRealTimers();
  });

  it("waits for SSE state updates when preferSse is enabled", async () => {
    vi.useFakeTimers();
    let current: EditorialWorkflowState | null = {
      project_id: "project-1",
      current_phase: "outline",
      phase_status: WORKFLOW_PHASE_STATUS.IN_PROGRESS,
      research_findings: [],
      outline: [],
      slide_drafts: [],
      status: "draft",
    };
    const refreshState = vi.fn(async () => current);

    const waitPromise = waitUntilWorkflowReadyWithTransport(
      () => current,
      refreshState,
      { preferSse: true, intervalMs: 10, maxAttempts: 3 },
    );

    await vi.advanceTimersByTimeAsync(10);
    current = {
      ...current,
      phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
      outline: [{ title: "Intro" }],
    };
    await vi.advanceTimersByTimeAsync(10);

    await expect(waitPromise).resolves.toMatchObject({
      outline: [{ title: "Intro" }],
    });
    expect(refreshState).not.toHaveBeenCalled();
    vi.useRealTimers();
  });

  it("returns failed and rejected workflow states as ready", () => {
    expect(
      isWorkflowReady({
        project_id: "project-1",
        current_phase: "research",
        phase_status: WORKFLOW_PHASE_STATUS.FAILED,
        research_findings: [],
        outline: [],
        slide_drafts: [],
        status: "draft",
      }),
    ).toBe(true);
    expect(
      isWorkflowReady({
        project_id: "project-1",
        current_phase: "research",
        phase_status: WORKFLOW_PHASE_STATUS.REJECTED,
        research_findings: [],
        outline: [],
        slide_drafts: [],
        status: "draft",
      }),
    ).toBe(true);
  });

  it("requires phase artifacts before awaiting_human counts as ready", () => {
    expect(
      isWorkflowReady({
        project_id: "project-1",
        current_phase: "research",
        phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
        research_findings: [],
        outline: [],
        slide_drafts: [],
        status: "draft",
      }),
    ).toBe(false);
    expect(
      isWorkflowReady({
        project_id: "project-1",
        current_phase: "research",
        phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
        research_findings: [{ title: "Finding" }],
        outline: [],
        slide_drafts: [],
        status: "draft",
      }),
    ).toBe(true);
  });

  it("evaluates artifact readiness per editorial phase", () => {
    const base: EditorialWorkflowState = {
      project_id: "project-1",
      current_phase: EDITORIAL_PHASES.RESEARCH,
      phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
      research_findings: [],
      outline: [],
      slide_drafts: [],
      status: "draft",
    };

    expect(
      hasPhaseArtifacts({ ...base, research_findings: [{ title: "A" }] }),
    ).toBe(true);
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
        slide_drafts: [{ draft_text: "Slide" }],
      }),
    ).toBe(false);
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
        caption: "Caption",
      }),
    ).toBe(true);
  });

  it("validates async resume acceptance payloads strictly", () => {
    expect(
      isResumeAcceptedResponse({
        accepted: true,
        project_id: "project-1",
        current_phase: "research",
        phase_status: WORKFLOW_PHASE_STATUS.IN_PROGRESS,
        lock_version: 2,
      }),
    ).toBe(true);
    expect(isResumeAcceptedResponse(null)).toBe(false);
    expect(isResumeAcceptedResponse({ accepted: true })).toBe(false);
  });

  it("parses workflow events and rejects malformed JSON", () => {
    expect(parseWorkflowEvent('{"event":"progress"}')).toEqual({
      event: "progress",
    });
    expect(parseWorkflowEvent("{invalid")).toBeNull();
  });

  it("reads API errors from string and array validation payloads", async () => {
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
            detail: [{ msg: "bad field" }, { msg: "missing" }],
          }),
        } as Response,
        "fallback",
      ),
    ).resolves.toBe("bad field, missing");
    await expect(
      readApiError(
        {
          json: async () => {
            throw new Error("broken");
          },
        } as unknown as Response,
        "fallback",
      ),
    ).resolves.toBe("fallback");
  });

  it("appends phases only once and ignores empty values", () => {
    expect(appendUniquePhase(["research"], "research")).toEqual(["research"]);
    expect(appendUniquePhase(["research"], undefined)).toEqual(["research"]);
    expect(appendUniquePhase(["research"], "outline")).toEqual([
      "research",
      "outline",
    ]);
  });

  it("classifies all resume transport failure statuses", () => {
    expect(isResumeTransportFailure(HTTP_STATUS.BAD_GATEWAY)).toBe(true);
    expect(isResumeTransportFailure(HTTP_STATUS.SERVICE_UNAVAILABLE)).toBe(
      true,
    );
    expect(isResumeTransportFailure(HTTP_STATUS.GATEWAY_TIMEOUT)).toBe(true);
  });

  it("merges full workflow snapshots using phase aliases", () => {
    const merged = mergeWorkflowState("project-1", null, {
      phase: "outline",
      phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
      research_findings: [],
      outline: [{ title: "Intro" }],
      slide_drafts: [],
      status: "draft",
    });

    expect(merged.current_phase).toBe("outline");
    expect(merged.project_id).toBe("project-1");
  });

  it("uses partial merge when payload lacks full workflow arrays", () => {
    const previous: EditorialWorkflowState = {
      project_id: "project-1",
      current_phase: "content",
      phase_status: WORKFLOW_PHASE_STATUS.IN_PROGRESS,
      research_findings: [{ title: "Finding" }],
      outline: [{ title: "Intro" }],
      slide_drafts: [{ draft_text: "Body" }],
      status: "draft",
    };

    const merged = mergeWorkflowState("project-1", previous, {
      phase: "content",
      slide_drafts: [{ draft_text: "Updated body" }],
    });

    expect(merged.slide_drafts).toEqual([{ draft_text: "Updated body" }]);
    expect(merged.outline).toEqual([{ title: "Intro" }]);
  });

  it("detects final review artifacts from blog markdown and rubric scores", () => {
    expect(
      hasPhaseArtifacts({
        project_id: "project-1",
        current_phase: EDITORIAL_PHASES.FINAL_REVIEW,
        phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
        research_findings: [],
        outline: [],
        slide_drafts: [],
        blog_markdown: "# Final post",
        status: "draft",
      }),
    ).toBe(true);
    expect(
      hasPhaseArtifacts({
        project_id: "project-1",
        current_phase: EDITORIAL_PHASES.FINAL_REVIEW,
        phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
        research_findings: [],
        outline: [],
        slide_drafts: [],
        rubric_scores: { clarity: 90 },
        status: "draft",
      }),
    ).toBe(true);
  });

  it("returns the final refresh result after exhausting poll attempts", async () => {
    vi.useFakeTimers();
    let attempts = 0;
    const refreshState = vi.fn(async () => {
      attempts += 1;
      if (attempts < 3) {
        return {
          project_id: "project-1",
          current_phase: "outline",
          phase_status: WORKFLOW_PHASE_STATUS.IN_PROGRESS,
          research_findings: [],
          outline: [],
          slide_drafts: [],
          status: "draft",
        };
      }
      return {
        project_id: "project-1",
        current_phase: "outline",
        phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
        research_findings: [],
        outline: [{ title: "Intro" }],
        slide_drafts: [],
        status: "draft",
      };
    });

    const waitPromise = waitUntilWorkflowReadyWithTransport(
      () => null,
      refreshState,
      { preferSse: false, intervalMs: 10, maxAttempts: 2 },
    );

    await vi.advanceTimersByTimeAsync(40);
    await expect(waitPromise).resolves.toMatchObject({
      outline: [{ title: "Intro" }],
    });
    vi.useRealTimers();
  });

  it("returns the final SSE snapshot after preferSse polling exhausts attempts", async () => {
    vi.useFakeTimers();
    const inProgressState: EditorialWorkflowState = {
      project_id: "project-1",
      current_phase: "outline",
      phase_status: WORKFLOW_PHASE_STATUS.IN_PROGRESS,
      research_findings: [],
      outline: [],
      slide_drafts: [],
      status: "draft",
    };
    const readyState: EditorialWorkflowState = {
      ...inProgressState,
      phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
      outline: [{ title: "Intro" }],
    };
    let reads = 0;
    const refreshState = vi.fn(async () => null);

    const waitPromise = waitUntilWorkflowReadyWithTransport(
      () => {
        reads += 1;
        return reads > 2 ? readyState : inProgressState;
      },
      refreshState,
      { preferSse: true, intervalMs: 10, maxAttempts: 2 },
    );

    await vi.advanceTimersByTimeAsync(30);
    await expect(waitPromise).resolves.toMatchObject({
      outline: [{ title: "Intro" }],
    });
    expect(refreshState).not.toHaveBeenCalled();
    vi.useRealTimers();
  });

  it("leaves review_required payloads unchanged without gate data", () => {
    const payload = resolveWorkflowEventPayload({
      event: EDITORIAL_WORKFLOW_SSE_EVENTS.REVIEW_REQUIRED,
      phase: "research",
      phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
    });

    expect(payload.gate_payload).toBeUndefined();
    expect(payload.phase).toBe("research");
  });
});
