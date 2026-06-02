/**
 * Mutation-killing tests for editorial workflow SSE hook branches.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import {
  EDITORIAL_WORKFLOW_POLL_BACKOFF_MS,
  EDITORIAL_WORKFLOW_SSE_EVENTS,
  EDITORIAL_WORKFLOW_TRANSPORT_MODE,
} from "@/constants/editorial-workflow";
import type { EditorialWorkflowTransportMode } from "@/constants/editorial-workflow";
import { WORKFLOW_PHASE_STATUS } from "@/constants/workflow";
import type { EditorialWorkflowState } from "@/features/blog/types-ai";
import { useEditorialWorkflowSse } from "./use-editorial-workflow-sse";

class MockEventSource {
  static readonly CONNECTING = 0;
  static readonly OPEN = 1;
  static readonly CLOSED = 2;
  static instances: MockEventSource[] = [];
  static lastInit: EventSourceInit | undefined;

  readyState = MockEventSource.CONNECTING;
  onmessage: ((event: MessageEvent<string>) => void) | null = null;
  onerror: (() => void) | null = null;
  onopen: (() => void) | null = null;
  private listeners = new Map<
    string,
    Array<(event: MessageEvent<string>) => void>
  >();

  constructor(
    public url: string,
    init?: EventSourceInit,
  ) {
    MockEventSource.lastInit = init;
    MockEventSource.instances.push(this);
  }

  addEventListener(
    type: string,
    listener: (event: MessageEvent<string>) => void,
  ): void {
    const handlers = this.listeners.get(type) ?? [];
    handlers.push(listener);
    this.listeners.set(type, handlers);
  }

  close = vi.fn(() => {
    this.readyState = MockEventSource.CLOSED;
  });

  emit(type: string, data: unknown): void {
    const event = { data: JSON.stringify(data) } as MessageEvent<string>;
    const handlers = this.listeners.get(type) ?? [];
    handlers.forEach((handler) => handler(event));
    this.onmessage?.(event);
  }

  open(): void {
    this.readyState = MockEventSource.OPEN;
    this.onopen?.();
  }

  fail(): void {
    this.onerror?.();
  }
}

const originalEventSource = globalThis.EventSource;

const baseState: EditorialWorkflowState = {
  project_id: "project-1",
  current_phase: "research",
  phase_status: WORKFLOW_PHASE_STATUS.IN_PROGRESS,
  research_findings: [],
  outline: [],
  slide_drafts: [],
  status: "draft",
};

function renderSseHook(
  overrides?: Partial<{
    projectId: string;
    state: EditorialWorkflowState | null;
    transportMode: EditorialWorkflowTransportMode;
  }>,
) {
  const setState = vi.fn();
  const setPhaseEvents = vi.fn();
  const setTransportMode = vi.fn();
  const setError = vi.fn();
  const refreshState = vi.fn(async () => baseState);

  const hook = renderHook(
    ({ projectId, state, transportMode }) =>
      useEditorialWorkflowSse({
        projectId,
        sseEnabled: Boolean(state?.current_phase),
        state,
        transportMode,
        setState,
        setPhaseEvents,
        setTransportMode,
        setError,
        refreshState,
      }),
    {
      initialProps: {
        projectId: overrides?.projectId ?? "project-1",
        state: overrides?.state ?? baseState,
        transportMode:
          overrides?.transportMode ?? EDITORIAL_WORKFLOW_TRANSPORT_MODE.SSE,
      },
    },
  );

  return {
    ...hook,
    setState,
    setPhaseEvents,
    setTransportMode,
    setError,
    refreshState,
  };
}

beforeEach(() => {
  MockEventSource.instances = [];
  MockEventSource.lastInit = undefined;
  vi.stubEnv("NEXT_PUBLIC_API_URL", "http://localhost:8000");
  // @ts-expect-error — swap in the mock for the duration of each test.
  globalThis.EventSource = MockEventSource;
});

afterEach(() => {
  globalThis.EventSource = originalEventSource;
  vi.unstubAllEnvs();
  vi.useRealTimers();
});

describe("useEditorialWorkflowSse mutation coverage", () => {
  it("merges artifact SSE payloads into workflow state", async () => {
    const { setState } = renderSseHook();

    await waitFor(() => {
      expect(MockEventSource.instances).toHaveLength(1);
    });

    act(() => {
      MockEventSource.instances[0]?.emit(
        EDITORIAL_WORKFLOW_SSE_EVENTS.ARTIFACT,
        {
          event: EDITORIAL_WORKFLOW_SSE_EVENTS.ARTIFACT,
          phase: "content",
          artifact_type: "slide_drafts",
          data: [{ draft_text: "Slide 1" }],
        },
      );
    });

    expect(setState).toHaveBeenCalledWith(
      expect.objectContaining({
        slide_drafts: [{ draft_text: "Slide 1" }],
      }),
    );
  });

  it("updates workflow state from generic SSE messages", async () => {
    const { setState } = renderSseHook();

    await waitFor(() => {
      expect(MockEventSource.instances).toHaveLength(1);
    });

    act(() => {
      MockEventSource.instances[0]?.onmessage?.({
        data: JSON.stringify({
          event: EDITORIAL_WORKFLOW_SSE_EVENTS.PHASE_CHANGED,
          phase: "outline",
          phase_status: WORKFLOW_PHASE_STATUS.IN_PROGRESS,
        }),
      } as MessageEvent<string>);
    });

    expect(setState).toHaveBeenCalledWith(
      expect.objectContaining({
        current_phase: "outline",
      }),
    );
  });

  it("returns to SSE mode when the stream opens", async () => {
    const { setTransportMode } = renderSseHook({
      transportMode: EDITORIAL_WORKFLOW_TRANSPORT_MODE.POLLING_FALLBACK,
    });

    await waitFor(() => {
      expect(MockEventSource.instances).toHaveLength(1);
    });

    act(() => {
      MockEventSource.instances[0]?.open();
    });

    expect(setTransportMode).toHaveBeenCalledWith(
      EDITORIAL_WORKFLOW_TRANSPORT_MODE.SSE,
    );
  });

  it("reconnects SSE after a disconnect using backoff", async () => {
    renderSseHook();

    await waitFor(() => {
      expect(MockEventSource.instances).toHaveLength(1);
    });

    vi.useFakeTimers();

    act(() => {
      MockEventSource.instances[0]?.fail();
    });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(EDITORIAL_WORKFLOW_POLL_BACKOFF_MS[0]);
    });

    expect(MockEventSource.instances.length).toBeGreaterThan(1);
    vi.useRealTimers();
  });

  it("clears polling timers when awaiting human review in fallback mode", async () => {
    const { refreshState, rerender } = renderSseHook({
      state: {
        ...baseState,
        phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
        research_findings: [{ title: "Finding" }],
      },
      transportMode: EDITORIAL_WORKFLOW_TRANSPORT_MODE.POLLING_FALLBACK,
    });

    vi.useFakeTimers();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(EDITORIAL_WORKFLOW_POLL_BACKOFF_MS[0]);
    });

    expect(refreshState).not.toHaveBeenCalled();

    rerender({
      projectId: "project-1",
      state: {
        ...baseState,
        phase_status: WORKFLOW_PHASE_STATUS.IN_PROGRESS,
      },
      transportMode: EDITORIAL_WORKFLOW_TRANSPORT_MODE.POLLING_FALLBACK,
    });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(EDITORIAL_WORKFLOW_POLL_BACKOFF_MS[0]);
    });

    expect(refreshState).toHaveBeenCalled();
  });

  it("exposes enterPollingFallback and stopPollingFallback handlers", async () => {
    const { result } = renderSseHook();

    await waitFor(() => {
      expect(MockEventSource.instances).toHaveLength(1);
    });

    act(() => {
      result.current.enterPollingFallback();
      result.current.stopPollingFallback();
    });
  });

  it("creates EventSource with credentials enabled", async () => {
    renderSseHook();

    await waitFor(() => {
      expect(MockEventSource.instances).toHaveLength(1);
    });

    expect(MockEventSource.lastInit).toEqual({ withCredentials: true });
  });

  it("closes SSE and clears timers on unmount", async () => {
    const { unmount } = renderSseHook();

    await waitFor(() => {
      expect(MockEventSource.instances).toHaveLength(1);
    });

    const source = MockEventSource.instances[0];
    unmount();

    expect(source?.close).toHaveBeenCalled();
  });

  it("ignores SSE payloads that do not change workflow state", async () => {
    const { setState } = renderSseHook();

    await waitFor(() => {
      expect(MockEventSource.instances).toHaveLength(1);
    });

    setState.mockClear();

    act(() => {
      MockEventSource.instances[0]?.emit(EDITORIAL_WORKFLOW_SSE_EVENTS.ERROR, {
        event: EDITORIAL_WORKFLOW_SSE_EVENTS.ERROR,
        message: "background resume failed",
        recoverable: true,
      });
    });

    expect(setState).not.toHaveBeenCalled();
  });

  it("merges review_required-only payloads through the SSE merge gate", async () => {
    const { setState } = renderSseHook();

    await waitFor(() => {
      expect(MockEventSource.instances).toHaveLength(1);
    });

    setState.mockClear();

    act(() => {
      MockEventSource.instances[0]?.emit(
        EDITORIAL_WORKFLOW_SSE_EVENTS.REVIEW_REQUIRED,
        {
          event: EDITORIAL_WORKFLOW_SSE_EVENTS.REVIEW_REQUIRED,
          phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
        },
      );
    });

    expect(setState).toHaveBeenCalled();
  });

  it("merges artifact-only payloads through the SSE merge gate", async () => {
    const { setState } = renderSseHook();

    await waitFor(() => {
      expect(MockEventSource.instances).toHaveLength(1);
    });

    setState.mockClear();

    act(() => {
      MockEventSource.instances[0]?.emit(
        EDITORIAL_WORKFLOW_SSE_EVENTS.ARTIFACT,
        {
          event: EDITORIAL_WORKFLOW_SSE_EVENTS.ARTIFACT,
          artifact_type: "outline",
          data: [{ title: "Intro" }],
        },
      );
    });

    expect(setState).toHaveBeenCalled();
  });

  it("updates workflow state when only phase_status changes", async () => {
    const { setState } = renderSseHook();

    await waitFor(() => {
      expect(MockEventSource.instances).toHaveLength(1);
    });

    setState.mockClear();

    act(() => {
      MockEventSource.instances[0]?.emit(
        EDITORIAL_WORKFLOW_SSE_EVENTS.PROGRESS,
        {
          event: EDITORIAL_WORKFLOW_SSE_EVENTS.PROGRESS,
          phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
        },
      );
    });

    expect(setState).toHaveBeenCalledWith(
      expect.objectContaining({
        phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
      }),
    );
  });

  it("does not append empty phases to phase events", async () => {
    const { setPhaseEvents } = renderSseHook();

    await waitFor(() => {
      expect(MockEventSource.instances).toHaveLength(1);
    });

    setPhaseEvents.mockClear();

    act(() => {
      MockEventSource.instances[0]?.emit(
        EDITORIAL_WORKFLOW_SSE_EVENTS.PROGRESS,
        {
          event: EDITORIAL_WORKFLOW_SSE_EVENTS.PROGRESS,
          phase: "",
          phase_status: WORKFLOW_PHASE_STATUS.IN_PROGRESS,
        },
      );
    });

    expect(setPhaseEvents).not.toHaveBeenCalled();
  });

  it("stops rescheduling polls once workflow reaches awaiting human", async () => {
    const readyState: EditorialWorkflowState = {
      ...baseState,
      phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
      research_findings: [{ title: "Finding" }],
    };

    const { refreshState, rerender } = renderSseHook({
      transportMode: EDITORIAL_WORKFLOW_TRANSPORT_MODE.POLLING_FALLBACK,
    });
    refreshState.mockImplementation(async () => {
      rerender({
        projectId: "project-1",
        state: readyState,
        transportMode: EDITORIAL_WORKFLOW_TRANSPORT_MODE.POLLING_FALLBACK,
      });
      return readyState;
    });

    vi.useFakeTimers();

    rerender({
      projectId: "project-1",
      state: baseState,
      transportMode: EDITORIAL_WORKFLOW_TRANSPORT_MODE.POLLING_FALLBACK,
    });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(EDITORIAL_WORKFLOW_POLL_BACKOFF_MS[0]);
    });

    const callsAfterReady = refreshState.mock.calls.length;

    await act(async () => {
      await vi.advanceTimersByTimeAsync(
        EDITORIAL_WORKFLOW_POLL_BACKOFF_MS[1] ?? 10_000,
      );
    });

    expect(refreshState.mock.calls.length).toBe(callsAfterReady);
    vi.useRealTimers();
  });

  it("surfaces non-recoverable errors only for string messages", async () => {
    const { setError } = renderSseHook();

    await waitFor(() => {
      expect(MockEventSource.instances).toHaveLength(1);
    });

    act(() => {
      MockEventSource.instances[0]?.emit(EDITORIAL_WORKFLOW_SSE_EVENTS.ERROR, {
        event: EDITORIAL_WORKFLOW_SSE_EVENTS.ERROR,
        message: 404,
        recoverable: false,
      });
    });

    expect(setError).not.toHaveBeenCalled();
  });

  it("reopens SSE against a new project id when the hook project changes", async () => {
    const { rerender } = renderSseHook({ projectId: "project-1" });

    await waitFor(() => {
      expect(MockEventSource.instances[0]?.url).toContain("project-1");
    });

    rerender({
      projectId: "project-2",
      state: baseState,
      transportMode: EDITORIAL_WORKFLOW_TRANSPORT_MODE.SSE,
    });

    await waitFor(() => {
      expect(MockEventSource.instances.at(-1)?.url).toContain("project-2");
    });
  });

  it("ignores empty SSE payloads that do not affect workflow state", async () => {
    const { setState } = renderSseHook();

    await waitFor(() => {
      expect(MockEventSource.instances).toHaveLength(1);
    });

    setState.mockClear();

    act(() => {
      MockEventSource.instances[0]?.onmessage?.({
        data: JSON.stringify({ event: "heartbeat" }),
      } as MessageEvent<string>);
    });

    expect(setState).not.toHaveBeenCalled();
  });

  it("uses nested phase_progress-only payloads to update workflow state", async () => {
    const { setState } = renderSseHook();

    await waitFor(() => {
      expect(MockEventSource.instances).toHaveLength(1);
    });

    setState.mockClear();

    act(() => {
      MockEventSource.instances[0]?.emit(
        EDITORIAL_WORKFLOW_SSE_EVENTS.PROGRESS,
        {
          event: EDITORIAL_WORKFLOW_SSE_EVENTS.PROGRESS,
          phase_progress: { current: 3, total: 8, label: "Slide 3 of 8" },
        },
      );
    });

    expect(setState).toHaveBeenCalledWith(
      expect.objectContaining({
        phase_progress: { current: 3, total: 8, label: "Slide 3 of 8" },
      }),
    );
  });

  it("merges payloads that only provide current_phase", async () => {
    const { setState } = renderSseHook();

    await waitFor(() => {
      expect(MockEventSource.instances).toHaveLength(1);
    });

    setState.mockClear();

    act(() => {
      MockEventSource.instances[0]?.emit(
        EDITORIAL_WORKFLOW_SSE_EVENTS.PHASE_CHANGED,
        {
          event: EDITORIAL_WORKFLOW_SSE_EVENTS.PHASE_CHANGED,
          current_phase: "outline",
        },
      );
    });

    expect(setState).toHaveBeenCalledWith(
      expect.objectContaining({
        current_phase: "outline",
      }),
    );
  });

  it("clears reconnect timers when the hook unmounts after SSE failure", async () => {
    const { unmount } = renderSseHook();

    await waitFor(() => {
      expect(MockEventSource.instances).toHaveLength(1);
    });

    vi.useFakeTimers();

    act(() => {
      MockEventSource.instances[0]?.fail();
    });

    unmount();

    const instancesBeforeReconnect = MockEventSource.instances.length;

    await act(async () => {
      await vi.advanceTimersByTimeAsync(EDITORIAL_WORKFLOW_POLL_BACKOFF_MS[0]);
    });

    expect(MockEventSource.instances.length).toBe(instancesBeforeReconnect);
    vi.useRealTimers();
  });

  it("does not schedule fallback polls while SSE transport is primary", async () => {
    const { refreshState, rerender } = renderSseHook({
      transportMode: EDITORIAL_WORKFLOW_TRANSPORT_MODE.SSE,
    });

    vi.useFakeTimers();

    rerender({
      projectId: "project-1",
      state: {
        ...baseState,
        phase_status: WORKFLOW_PHASE_STATUS.IN_PROGRESS,
      },
      transportMode: EDITORIAL_WORKFLOW_TRANSPORT_MODE.SSE,
    });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(EDITORIAL_WORKFLOW_POLL_BACKOFF_MS[0]);
    });

    expect(refreshState).not.toHaveBeenCalled();
    vi.useRealTimers();
  });
});
