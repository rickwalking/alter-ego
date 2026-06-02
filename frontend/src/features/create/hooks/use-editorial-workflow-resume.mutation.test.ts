/**
 * Mutation-killing tests for editorial workflow resume hook branches.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { createRef } from "react";
import { HTTP_STATUS } from "@/constants/api";
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

const inProgressState: EditorialWorkflowState = {
  project_id: "project-1",
  current_phase: "research",
  phase_status: WORKFLOW_PHASE_STATUS.IN_PROGRESS,
  research_findings: [],
  outline: [],
  slide_drafts: [],
  status: "draft",
  lock_version: 1,
};

const readyState: EditorialWorkflowState = {
  ...inProgressState,
  phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
  research_findings: [{ title: "Finding" }],
};

function createHookOptions(overrides?: {
  lockVersion?: number;
  workflowState?: EditorialWorkflowState | null;
  transportMode?: EditorialWorkflowTransportMode;
}) {
  const workflowStateRef = createRef<EditorialWorkflowState | null>();
  workflowStateRef.current =
    overrides?.workflowState === undefined
      ? inProgressState
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
  const setPhaseEvents = vi.fn((value) => {
    if (typeof value === "function") {
      return value([]);
    }
    return value;
  });
  const setLoading = vi.fn();
  const setError = vi.fn();
  const enterPollingFallback = vi.fn();
  const stopPollingFallback = vi.fn();
  const refreshState = vi.fn(async () => workflowStateRef.current);

  return {
    workflowStateRef,
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
          : inProgressState.lock_version,
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
  vi.restoreAllMocks();
});

describe("useEditorialWorkflowResume mutation coverage", () => {
  it("optimistically marks in-progress state before resume completes", async () => {
    mockAuthenticatedFetch.mockResolvedValue({
      ok: true,
      status: HTTP_STATUS.OK,
      json: async () => readyState,
    } as Response);

    const { hookParams, workflowStateRef } = createHookOptions();
    const { result } = renderHook(() => useEditorialWorkflowResume(hookParams));

    await act(async () => {
      await result.current.resume("approve");
    });

    expect(workflowStateRef.current?.phase_status).toBe(
      WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
    );
  });

  it("defaults expected_version to 1 when lock version is missing", async () => {
    mockAuthenticatedFetch.mockImplementation(async (_url, init) => {
      const body = JSON.parse(String(init?.body)) as {
        expected_version: number;
      };
      expect(body.expected_version).toBe(1);
      return {
        ok: true,
        status: HTTP_STATUS.OK,
        json: async () => readyState,
      } as Response;
    });

    const { hookParams, refreshState } = createHookOptions({
      lockVersion: undefined,
    });
    refreshState.mockResolvedValue(null);
    const { result } = renderHook(() => useEditorialWorkflowResume(hookParams));

    await act(async () => {
      await result.current.resume("approve");
    });
  });

  it("includes only targetPhase in structured feedback when editedText is absent", async () => {
    mockAuthenticatedFetch.mockImplementation(async (_url, init) => {
      const body = JSON.parse(String(init?.body)) as {
        structured_feedback?: { target_phase?: string; edited_text?: string };
      };
      expect(body.structured_feedback).toEqual({ target_phase: "content" });
      return {
        ok: true,
        status: HTTP_STATUS.OK,
        json: async () => readyState,
      } as Response;
    });

    const { hookParams } = createHookOptions();
    const { result } = renderHook(() => useEditorialWorkflowResume(hookParams));

    await act(async () => {
      await result.current.resume("revise", "Rewrite", {
        targetPhase: "content",
      });
    });
  });

  it("polls for ready state when synchronous resume payload is not ready", async () => {
    mockAuthenticatedFetch.mockResolvedValue({
      ok: true,
      status: HTTP_STATUS.OK,
      json: async () => inProgressState,
    } as Response);

    const waitSpy = vi
      .spyOn(editorialWorkflowUtils, "waitUntilWorkflowReadyWithTransport")
      .mockResolvedValue(readyState);

    const { hookParams, enterPollingFallback } = createHookOptions();
    const { result } = renderHook(() => useEditorialWorkflowResume(hookParams));

    await act(async () => {
      await result.current.resume("approve");
    });

    expect(enterPollingFallback).toHaveBeenCalled();
    expect(waitSpy).toHaveBeenCalled();
    waitSpy.mockRestore();
  });

  it("updates lock version on async accepted responses that are not ready yet", async () => {
    mockAuthenticatedFetch.mockResolvedValue({
      ok: true,
      status: HTTP_STATUS.ACCEPTED,
      json: async () => ({
        accepted: true,
        project_id: "project-1",
        current_phase: "research",
        phase_status: WORKFLOW_PHASE_STATUS.IN_PROGRESS,
        lock_version: 4,
      }),
    } as Response);

    const waitSpy = vi
      .spyOn(editorialWorkflowUtils, "waitUntilWorkflowReadyWithTransport")
      .mockResolvedValue(readyState);

    const { hookParams, setState } = createHookOptions();
    const { result } = renderHook(() => useEditorialWorkflowResume(hookParams));

    await act(async () => {
      await result.current.resume("approve");
    });

    expect(
      setState.mock.calls.some(([value]) => {
        if (typeof value !== "function") {
          return false;
        }
        const next = value(inProgressState);
        return next?.lock_version === 4;
      }),
    ).toBe(true);
    waitSpy.mockRestore();
  });

  it("returns immediately when async accepted response leaves workflow ready", async () => {
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

    const { hookParams, workflowStateRef } = createHookOptions({
      workflowState: readyState,
    });
    const waitSpy = vi.spyOn(
      editorialWorkflowUtils,
      "waitUntilWorkflowReadyWithTransport",
    );
    const { result } = renderHook(() => useEditorialWorkflowResume(hookParams));

    await act(async () => {
      await result.current.resume("approve");
    });

    expect(waitSpy).not.toHaveBeenCalled();
    expect(workflowStateRef.current?.lock_version).toBe(2);
    waitSpy.mockRestore();
  });

  it("appends the current phase after finalizeResume succeeds", async () => {
    mockAuthenticatedFetch.mockResolvedValue({
      ok: true,
      status: HTTP_STATUS.OK,
      json: async () => ({
        ...readyState,
        current_phase: "outline",
        outline: [{ title: "Intro" }],
      }),
    } as Response);

    const { hookParams, setPhaseEvents } = createHookOptions();
    const { result } = renderHook(() => useEditorialWorkflowResume(hookParams));

    await act(async () => {
      await result.current.resume("approve");
    });

    expect(setPhaseEvents).toHaveBeenCalled();
  });

  it("uses polling transport preference from transportModeRef", async () => {
    mockAuthenticatedFetch.mockResolvedValue({
      ok: true,
      status: HTTP_STATUS.OK,
      json: async () => inProgressState,
    } as Response);

    const waitSpy = vi
      .spyOn(editorialWorkflowUtils, "waitUntilWorkflowReadyWithTransport")
      .mockResolvedValue(readyState);

    const { hookParams } = createHookOptions({
      transportMode: EDITORIAL_WORKFLOW_TRANSPORT_MODE.POLLING_FALLBACK,
    });
    const { result } = renderHook(() => useEditorialWorkflowResume(hookParams));

    await act(async () => {
      await result.current.resume("approve");
    });

    expect(waitSpy).toHaveBeenCalledWith(
      expect.any(Function),
      expect.any(Function),
      expect.objectContaining({ preferSse: false }),
    );
    waitSpy.mockRestore();
  });

  it("refreshes workflow state after resume failures", async () => {
    mockAuthenticatedFetch.mockResolvedValue({
      ok: false,
      status: HTTP_STATUS.CONFLICT,
      json: async () => ({ detail: "version_conflict" }),
    } as Response);

    const { hookParams, refreshState } = createHookOptions();
    const { result } = renderHook(() => useEditorialWorkflowResume(hookParams));

    await act(async () => {
      try {
        await result.current.resume("approve");
      } catch {
        // expected
      }
    });

    expect(refreshState).toHaveBeenCalled();
  });
});
