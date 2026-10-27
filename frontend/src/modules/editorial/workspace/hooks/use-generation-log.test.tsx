import { createElement, type ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { EditorialWorkflowState } from "@/modules/publishing";
import { useGenerationLog } from "./use-generation-log";

vi.mock("@/lib/api-client", () => ({ apiCall: vi.fn() }));

import { apiCall } from "@/lib/api-client";

const mockApiCall = vi.mocked(apiCall);
const runId = "11111111-1111-1111-1111-111111111111";
const eventId = "22222222-2222-2222-2222-222222222222";

function page(nextCursor: string | null) {
  return {
    project_id: "p1",
    next_cursor: nextCursor,
    runs: [
      {
        id: runId,
        kind: "workflow_resume",
        status: "running",
        queued_at: "2026-10-26T12:00:00Z",
        started_at: "2026-10-26T12:00:01Z",
        finished_at: null,
        duration_ms: null,
        attempts: 1,
        error_code: null,
      },
    ],
    events: [
      {
        id: eventId,
        generation_run_id: runId,
        event_type: "run_started",
        phase: null,
        outcome: "running",
        occurred_at: "2026-10-26T12:00:01Z",
        duration_ms: null,
        attempt: 1,
        error_code: null,
        message_code: "generation_started",
        details: {},
        langfuse_trace_id: null,
        langfuse_trace_url: null,
      },
    ],
  };
}

const state: EditorialWorkflowState = {
  project_id: "p1",
  current_phase: "content",
  phase_status: "in_progress",
  research_findings: [],
  outline: [],
  slide_drafts: [],
  status: "draft",
  run_stage: "generating",
};

let queryClient: QueryClient;

function wrapper({ children }: { children: ReactNode }) {
  return createElement(QueryClientProvider, { client: queryClient }, children);
}

beforeEach(() => {
  vi.clearAllMocks();
  queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: Infinity } },
  });
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("useGenerationLog", () => {
  /** Scenario: Generation log groups runs and phases accessibly */
  it("loads bounded pages with the event cursor", async () => {
    mockApiCall
      .mockResolvedValueOnce(page("cursor-1"))
      .mockResolvedValueOnce(page(null));
    const { result } = renderHook(() => useGenerationLog("p1", null), {
      wrapper,
    });
    await waitFor(() =>
      expect(result.current.data?.pages.length).toBeGreaterThan(0),
    );

    await result.current.fetchNextPage();
    await waitFor(() => expect(result.current.data?.pages).toHaveLength(2));

    expect(mockApiCall).toHaveBeenNthCalledWith(
      1,
      "/api/carousels/p1/generation-log",
      expect.anything(),
    );
    expect(mockApiCall).toHaveBeenNthCalledWith(
      2,
      "/api/carousels/p1/generation-log?before=cursor-1",
      expect.anything(),
    );
    expect(result.current.data?.pages).toHaveLength(2);
  });

  /** Scenario: Generation log refreshes from existing workflow updates */
  it("invalidates on workflow changes without creating a timer or stream", async () => {
    mockApiCall.mockResolvedValue(page(null));
    const interval = vi.spyOn(globalThis, "setInterval");
    const invalidate = vi.spyOn(queryClient, "invalidateQueries");
    const stream = vi.fn();
    vi.stubGlobal("EventSource", stream);
    const { result, rerender } = renderHook(
      ({ workflow }) => useGenerationLog("p1", workflow),
      { wrapper, initialProps: { workflow: state } },
    );
    expect(interval).not.toHaveBeenCalled();
    await waitFor(() =>
      expect(result.current.data?.pages.length).toBeGreaterThan(0),
    );
    const timerCallsBeforeUpdate = interval.mock.calls.length;
    rerender({ workflow: state });
    rerender({
      workflow: { ...state, outline: [{ heading: "Artifact update" }] },
    });
    expect(interval.mock.calls).toHaveLength(timerCallsBeforeUpdate);

    await waitFor(() => expect(invalidate).toHaveBeenCalled());
    await waitFor(() => expect(mockApiCall).toHaveBeenCalledTimes(2));
    expect(stream).not.toHaveBeenCalled();
    vi.unstubAllGlobals();
  });
});
