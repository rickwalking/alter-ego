import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { createRef } from "react";
import { HTTP_STATUS, HTTP_METHODS } from "@/constants/api";
import { EDITORIAL_WORKFLOW_TRANSPORT_MODE } from "@/constants/editorial-workflow";
import type { EditorialWorkflowTransportMode } from "@/constants/editorial-workflow";
import { WORKFLOW_PHASE_STATUS } from "@/constants/workflow";
import type { EditorialWorkflowState } from "@/features/blog/types-ai";
import { useEditorialWorkflowResume } from "./use-editorial-workflow-resume";
import * as editorialWorkflowUtils from "./use-editorial-workflow-utils";

vi.mock("@/lib/authenticated-fetch", () => ({
  authenticatedFetch: vi.fn(),
}));

import { authenticatedFetch } from "@/lib/authenticated-fetch";

const mockAuthenticatedFetch = vi.mocked(authenticatedFetch);

const baseState: EditorialWorkflowState = {
  project_id: "project-1",
  current_phase: "research",
  phase_status: WORKFLOW_PHASE_STATUS.IN_PROGRESS,
  research_findings: [],
  outline: [],
  slide_drafts: [],
  status: "draft",
  lock_version: 1,
};

function createHookOptions(overrides?: {
  lockVersion?: number;
  workflowState?: EditorialWorkflowState | null;
  transportMode?: EditorialWorkflowTransportMode;
}) {
  const workflowStateRef = createRef<EditorialWorkflowState | null>();
  workflowStateRef.current =
    overrides?.workflowState === undefined
      ? baseState
      : overrides.workflowState;
  const transportModeRef = createRef<EditorialWorkflowTransportMode>();
  transportModeRef.current =
    overrides?.transportMode ?? EDITORIAL_WORKFLOW_TRANSPORT_MODE.SSE;

  const setState = vi.fn(
    (
      value:
        | EditorialWorkflowState
        | null
        | ((
            prev: EditorialWorkflowState | null,
          ) => EditorialWorkflowState | null),
    ) => {
      if (typeof value === "function") {
        workflowStateRef.current = value(workflowStateRef.current);
      } else {
        workflowStateRef.current = value;
      }
    },
  );
  const setPhaseEvents = vi.fn();
  const setLoading = vi.fn();
  const setError = vi.fn();
  const enterPollingFallback = vi.fn();
  const stopPollingFallback = vi.fn();
  const refreshState = vi.fn(async () => workflowStateRef.current);

  return {
    workflowStateRef,
    transportModeRef,
    setState,
    setPhaseEvents,
    setLoading,
    setError,
    enterPollingFallback,
    stopPollingFallback,
    refreshState,
    hookParams: {
      projectId: "project-1",
      lockVersion:
        overrides !== undefined && "lockVersion" in overrides
          ? overrides.lockVersion
          : baseState.lock_version,
      translateError: (key: string) => `error.${key}`,
      workflowStateRef,
      transportModeRef,
      refreshState,
      setState,
      setPhaseEvents,
      setLoading,
      setError,
      enterPollingFallback,
      stopPollingFallback,
    },
  };
}

beforeEach(() => {
  mockAuthenticatedFetch.mockReset();
  vi.stubEnv("NEXT_PUBLIC_API_URL", "http://localhost:8000");
});

afterEach(() => {
  vi.unstubAllEnvs();
  vi.useRealTimers();
});

describe("useEditorialWorkflowResume", () => {
  // Regression (c858abd): the resume call must use the bare /api endpoint
  // path, NOT a NEXT_PUBLIC_API_URL-prefixed URL. The path already starts
  // with /api and nginx routes /api/* to the backend; prefixing produced
  // /api/api/... and a 404 right after approving the research phase.
  it("posts resume to the bare /api endpoint path (no NEXT_PUBLIC_API_URL prefix)", async () => {
    mockAuthenticatedFetch.mockResolvedValue({
      ok: true,
      status: HTTP_STATUS.OK,
      json: async () => ({
        ...baseState,
        phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
        research_findings: [{ title: "Finding" }],
      }),
    } as Response);

    const { hookParams } = createHookOptions();
    const { result } = renderHook(() => useEditorialWorkflowResume(hookParams));

    await act(async () => {
      await result.current.resume("approve");
    });

    expect(mockAuthenticatedFetch).toHaveBeenCalledWith(
      "/api/carousels/project-1/workflow/resume",
      expect.objectContaining({ method: HTTP_METHODS.POST }),
    );
    expect(mockAuthenticatedFetch).not.toHaveBeenCalledWith(
      "http://localhost:8000/api/carousels/project-1/workflow/resume",
      expect.anything(),
    );
  });

  it("returns synchronous resume responses when workflow artifacts are ready", async () => {
    mockAuthenticatedFetch.mockResolvedValue({
      ok: true,
      status: HTTP_STATUS.OK,
      json: async () => ({
        ...baseState,
        current_phase: "outline",
        phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
        outline: [{ title: "Intro" }],
      }),
    } as Response);

    const { hookParams, setState, stopPollingFallback } = createHookOptions();
    const { result } = renderHook(() => useEditorialWorkflowResume(hookParams));

    await act(async () => {
      await result.current.resume("approve");
    });

    expect(setState).toHaveBeenCalled();
    expect(stopPollingFallback).toHaveBeenCalled();
  });

  it("accepts async 202 responses and waits for SSE-ready workflow state", async () => {
    const readyState: EditorialWorkflowState = {
      ...baseState,
      current_phase: "outline",
      phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
      outline: [{ title: "Intro" }],
      lock_version: 2,
    };

    mockAuthenticatedFetch.mockResolvedValue({
      ok: true,
      status: HTTP_STATUS.ACCEPTED,
      json: async () => ({
        accepted: true,
        project_id: "project-1",
        current_phase: "research",
        phase_status: WORKFLOW_PHASE_STATUS.IN_PROGRESS,
        lock_version: 2,
      }),
    } as Response);

    const { hookParams, workflowStateRef } = createHookOptions();
    const { result } = renderHook(() => useEditorialWorkflowResume(hookParams));

    vi.useFakeTimers();
    await act(async () => {
      const resumePromise = result.current.resume("approve");
      workflowStateRef.current = readyState;
      await vi.advanceTimersByTimeAsync(5_100);
      await resumePromise;
    });

    expect(workflowStateRef.current?.current_phase).toBe("outline");
  });

  it("includes structured feedback fields in revise payloads", async () => {
    mockAuthenticatedFetch.mockImplementation(async (_url, init) => {
      const body = JSON.parse(String(init?.body)) as {
        structured_feedback?: { target_phase?: string; edited_text?: string };
      };
      expect(body.structured_feedback).toEqual({
        target_phase: "content",
        edited_text: "Rewrite intro",
      });
      return {
        ok: true,
        status: HTTP_STATUS.OK,
        json: async () => ({
          ...baseState,
          current_phase: "content",
          phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
          outline: [{ title: "Intro" }],
          slide_drafts: [{ draft_text: "Body" }],
        }),
      } as Response;
    });

    const { hookParams } = createHookOptions();
    const { result } = renderHook(() => useEditorialWorkflowResume(hookParams));

    await act(async () => {
      await result.current.resume("revise", "Rewrite intro", {
        targetPhase: "content",
        editedText: "Rewrite intro",
      });
    });
  });

  it("refreshes lock version when resume starts without one", async () => {
    const readyState: EditorialWorkflowState = {
      ...baseState,
      lock_version: 3,
      phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
      research_findings: [{ title: "Finding" }],
    };

    mockAuthenticatedFetch.mockImplementation(async (url, init) => {
      if (
        url === "/api/carousels/project-1/workflow/resume" &&
        init?.method === HTTP_METHODS.POST
      ) {
        const body = JSON.parse(String(init.body)) as {
          expected_version: number;
        };
        expect(body.expected_version).toBe(3);
        return {
          ok: true,
          status: HTTP_STATUS.OK,
          json: async () => readyState,
        } as Response;
      }
      throw new Error(`Unexpected fetch: ${String(url)}`);
    });

    const { hookParams, refreshState } = createHookOptions({
      lockVersion: undefined,
    });
    refreshState.mockResolvedValue(readyState);

    const { result } = renderHook(() => useEditorialWorkflowResume(hookParams));

    await act(async () => {
      await result.current.resume("approve");
    });

    expect(refreshState).toHaveBeenCalled();
  });

  it("surfaces client resume errors without entering polling recovery", async () => {
    mockAuthenticatedFetch.mockResolvedValue({
      ok: false,
      status: HTTP_STATUS.CONFLICT,
      json: async () => ({ detail: "version_conflict" }),
    } as Response);

    const { hookParams, setError, enterPollingFallback } = createHookOptions();
    const { result } = renderHook(() => useEditorialWorkflowResume(hookParams));

    let caught: unknown;
    await act(async () => {
      try {
        await result.current.resume("approve");
      } catch (error) {
        caught = error;
      }
    });

    expect(caught).toEqual(new Error("version_conflict"));
    expect(setError).toHaveBeenCalledWith("version_conflict");
    expect(enterPollingFallback).not.toHaveBeenCalled();
  });

  it("recovers from transport failures by polling workflow state", async () => {
    const readyState: EditorialWorkflowState = {
      ...baseState,
      current_phase: "outline",
      phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
      outline: [{ title: "Intro" }],
    };

    mockAuthenticatedFetch.mockResolvedValue({
      ok: false,
      status: HTTP_STATUS.INTERNAL_SERVER_ERROR,
      json: async () => ({ detail: "gateway timeout" }),
    } as Response);

    const { hookParams, enterPollingFallback, refreshState } =
      createHookOptions();
    refreshState.mockResolvedValue(readyState);
    const { result } = renderHook(() => useEditorialWorkflowResume(hookParams));

    vi.useFakeTimers();
    await act(async () => {
      const resumePromise = result.current.resume("approve");
      await vi.runAllTimersAsync();
      await resumePromise;
    });

    expect(enterPollingFallback).toHaveBeenCalled();
    expect(refreshState).toHaveBeenCalled();
  });

  it("recovers when resume fetch throws a network error", async () => {
    const readyState: EditorialWorkflowState = {
      ...baseState,
      current_phase: "outline",
      phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
      outline: [{ title: "Intro" }],
    };

    mockAuthenticatedFetch.mockRejectedValue(new TypeError("Failed to fetch"));

    const { hookParams, enterPollingFallback, refreshState } =
      createHookOptions();
    refreshState.mockResolvedValue(readyState);
    const { result } = renderHook(() => useEditorialWorkflowResume(hookParams));

    vi.useFakeTimers();
    await act(async () => {
      const resumePromise = result.current.resume("approve");
      await vi.runAllTimersAsync();
      await resumePromise;
    });

    expect(enterPollingFallback).toHaveBeenCalled();
  });

  it("rejects malformed async acceptance payloads", async () => {
    mockAuthenticatedFetch.mockResolvedValue({
      ok: true,
      status: HTTP_STATUS.ACCEPTED,
      json: async () => ({ accepted: false }),
    } as Response);

    const { hookParams, setError } = createHookOptions();
    const { result } = renderHook(() => useEditorialWorkflowResume(hookParams));

    let caught: unknown;
    await act(async () => {
      try {
        await result.current.resume("approve");
      } catch (error) {
        caught = error;
      }
    });

    expect(caught).toEqual(new Error("error.resumeFailed"));
    expect(setError).toHaveBeenCalledWith("error.resumeFailed");
  });

  it("includes feedback text in resume payloads", async () => {
    mockAuthenticatedFetch.mockImplementation(async (_url, init) => {
      const body = JSON.parse(String(init?.body)) as { feedback?: string };
      expect(body.feedback).toBe("Needs more detail");
      return {
        ok: true,
        status: HTTP_STATUS.OK,
        json: async () => ({
          ...baseState,
          phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
          research_findings: [{ title: "Finding" }],
        }),
      } as Response;
    });

    const { hookParams } = createHookOptions();
    const { result } = renderHook(() => useEditorialWorkflowResume(hookParams));

    await act(async () => {
      await result.current.resume("revise", "Needs more detail");
    });
  });

  it("marks in-progress state optimistically before resume completes", async () => {
    mockAuthenticatedFetch.mockResolvedValue({
      ok: true,
      status: HTTP_STATUS.OK,
      json: async () => ({
        ...baseState,
        phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
        research_findings: [{ title: "Finding" }],
      }),
    } as Response);

    const { hookParams, setState } = createHookOptions();
    const { result } = renderHook(() => useEditorialWorkflowResume(hookParams));

    await act(async () => {
      await result.current.resume("approve");
    });

    expect(setState).toHaveBeenCalledWith(expect.any(Function));
  });

  it("surfaces unknown resume errors for non-Error throws", async () => {
    mockAuthenticatedFetch.mockResolvedValue({
      ok: true,
      status: HTTP_STATUS.OK,
      json: async () => {
        throw "broken payload";
      },
    } as unknown as Response);

    const { hookParams, setError } = createHookOptions();
    const { result } = renderHook(() => useEditorialWorkflowResume(hookParams));

    let caught: unknown;
    await act(async () => {
      try {
        await result.current.resume("approve");
      } catch (error) {
        caught = error;
      }
    });

    expect(caught).toBe("broken payload");
    expect(setError).toHaveBeenCalledWith("error.resumeUnknown");
  });

  it("fails resume when polling never returns ready artifacts", async () => {
    mockAuthenticatedFetch.mockResolvedValue({
      ok: true,
      status: HTTP_STATUS.ACCEPTED,
      json: async () => ({
        accepted: true,
        project_id: "project-1",
        current_phase: "research",
        phase_status: WORKFLOW_PHASE_STATUS.IN_PROGRESS,
        lock_version: 2,
      }),
    } as Response);

    const waitSpy = vi
      .spyOn(editorialWorkflowUtils, "waitUntilWorkflowReadyWithTransport")
      .mockResolvedValue(null);

    const { hookParams } = createHookOptions();
    const { result } = renderHook(() => useEditorialWorkflowResume(hookParams));

    let caught: unknown;
    await act(async () => {
      try {
        await result.current.resume("approve");
      } catch (error) {
        caught = error;
      }
    });

    expect(caught).toEqual(new Error("error.resumeFailed"));
    waitSpy.mockRestore();
  });

  it("reads generic resume failures from non-client error responses", async () => {
    mockAuthenticatedFetch.mockResolvedValue({
      ok: false,
      status: HTTP_STATUS.FORBIDDEN,
      json: async () => ({ detail: "forbidden" }),
    } as Response);

    const { hookParams, setError } = createHookOptions();
    const { result } = renderHook(() => useEditorialWorkflowResume(hookParams));

    let caught: unknown;
    await act(async () => {
      try {
        await result.current.resume("approve");
      } catch (error) {
        caught = error;
      }
    });

    expect(caught).toEqual(new Error("forbidden"));
    expect(setError).toHaveBeenCalledWith("forbidden");
  });

  it("stops polling fallback after polled resume completes at human gate", async () => {
    const readyState: EditorialWorkflowState = {
      ...baseState,
      current_phase: "outline",
      phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
      outline: [{ title: "Intro" }],
    };

    mockAuthenticatedFetch.mockResolvedValue({
      ok: true,
      status: HTTP_STATUS.OK,
      json: async () => ({
        ...baseState,
        phase_status: WORKFLOW_PHASE_STATUS.IN_PROGRESS,
      }),
    } as Response);

    const waitSpy = vi
      .spyOn(editorialWorkflowUtils, "waitUntilWorkflowReadyWithTransport")
      .mockResolvedValue(readyState);

    const { hookParams, stopPollingFallback } = createHookOptions();
    const { result } = renderHook(() => useEditorialWorkflowResume(hookParams));

    await act(async () => {
      await result.current.resume("approve");
    });

    expect(stopPollingFallback).toHaveBeenCalled();
    waitSpy.mockRestore();
  });

  it("skips optimistic in-progress updates when workflow is already ready", async () => {
    const readyState: EditorialWorkflowState = {
      ...baseState,
      phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
      research_findings: [{ title: "Finding" }],
    };

    mockAuthenticatedFetch.mockResolvedValue({
      ok: true,
      status: HTTP_STATUS.OK,
      json: async () => readyState,
    } as Response);

    const { hookParams, setState } = createHookOptions({
      workflowState: readyState,
    });
    const { result } = renderHook(() => useEditorialWorkflowResume(hookParams));

    await act(async () => {
      await result.current.resume("approve");
    });

    const optimisticUpdates = setState.mock.calls.filter(
      ([value]) => typeof value === "function",
    );
    expect(
      optimisticUpdates.some(([value]) => {
        const updater = value as (
          prev: EditorialWorkflowState | null,
        ) => EditorialWorkflowState | null;
        return (
          updater(readyState)?.phase_status ===
          WORKFLOW_PHASE_STATUS.IN_PROGRESS
        );
      }),
    ).toBe(false);
  });
});
