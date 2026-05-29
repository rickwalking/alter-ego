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

  readyState = MockEventSource.CONNECTING;
  onmessage: ((event: MessageEvent<string>) => void) | null = null;
  onerror: (() => void) | null = null;
  onopen: (() => void) | null = null;
  private listeners = new Map<
    string,
    Array<(event: MessageEvent<string>) => void>
  >();

  constructor(public url: string) {
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
    ({ state, transportMode }) =>
      useEditorialWorkflowSse({
        projectId: "project-1",
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
  vi.stubEnv("NEXT_PUBLIC_API_URL", "http://localhost:8000");
  // @ts-expect-error — swap in the mock for the duration of each test.
  globalThis.EventSource = MockEventSource;
});

afterEach(() => {
  globalThis.EventSource = originalEventSource;
  vi.unstubAllEnvs();
  vi.useRealTimers();
});

describe("useEditorialWorkflowSse", () => {
  it("opens SSE with NEXT_PUBLIC_API_URL and credentials", async () => {
    renderSseHook();

    await waitFor(() => {
      expect(MockEventSource.instances).toHaveLength(1);
    });

    expect(MockEventSource.instances[0]?.url).toBe(
      "http://localhost:8000/api/carousels/project-1/workflow/stream",
    );
  });

  it("enters polling fallback when EventSource is unavailable", async () => {
    // @ts-expect-error — simulate browsers without SSE support.
    delete globalThis.EventSource;

    const { setTransportMode } = renderSseHook();

    await waitFor(() => {
      expect(setTransportMode).toHaveBeenCalledWith(
        EDITORIAL_WORKFLOW_TRANSPORT_MODE.POLLING_FALLBACK,
      );
    });
  });

  it("merges review_required gate payloads from SSE events", async () => {
    const { setState } = renderSseHook();

    await waitFor(() => {
      expect(MockEventSource.instances).toHaveLength(1);
    });

    act(() => {
      MockEventSource.instances[0]?.emit(
        EDITORIAL_WORKFLOW_SSE_EVENTS.REVIEW_REQUIRED,
        {
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
        },
      );
    });

    expect(setState).toHaveBeenCalledWith(
      expect.objectContaining({
        current_phase: "research",
        research_findings: [{ title: "Finding" }],
      }),
    );
  });

  it("ignores recoverable SSE error events", async () => {
    const { setError } = renderSseHook();

    await waitFor(() => {
      expect(MockEventSource.instances).toHaveLength(1);
    });

    act(() => {
      MockEventSource.instances[0]?.emit(EDITORIAL_WORKFLOW_SSE_EVENTS.ERROR, {
        event: EDITORIAL_WORKFLOW_SSE_EVENTS.ERROR,
        message: "background resume failed",
        recoverable: true,
      });
    });

    expect(setError).not.toHaveBeenCalled();
  });

  it("surfaces non-recoverable SSE error events", async () => {
    const { setError } = renderSseHook();

    await waitFor(() => {
      expect(MockEventSource.instances).toHaveLength(1);
    });

    act(() => {
      MockEventSource.instances[0]?.emit(EDITORIAL_WORKFLOW_SSE_EVENTS.ERROR, {
        event: EDITORIAL_WORKFLOW_SSE_EVENTS.ERROR,
        message: "workflow_phase_failed",
        recoverable: false,
      });
    });

    expect(setError).toHaveBeenCalledWith("workflow_phase_failed");
  });

  it("ignores malformed SSE payloads", async () => {
    const { setState } = renderSseHook();

    await waitFor(() => {
      expect(MockEventSource.instances).toHaveLength(1);
    });

    act(() => {
      MockEventSource.instances[0]?.onmessage?.({
        data: "{invalid-json",
      } as MessageEvent<string>);
    });

    expect(setState).not.toHaveBeenCalled();
  });

  it("switches to polling fallback when SSE disconnects", async () => {
    const { setTransportMode } = renderSseHook();

    await waitFor(() => {
      expect(MockEventSource.instances).toHaveLength(1);
    });

    act(() => {
      MockEventSource.instances[0]?.fail();
    });

    expect(setTransportMode).toHaveBeenCalledWith(
      EDITORIAL_WORKFLOW_TRANSPORT_MODE.POLLING_FALLBACK,
    );
  });

  it("polls workflow state with backoff while in polling fallback mode", async () => {
    const { refreshState, rerender } = renderSseHook();

    await waitFor(() => {
      expect(MockEventSource.instances).toHaveLength(1);
    });

    vi.useFakeTimers();

    act(() => {
      MockEventSource.instances[0]?.fail();
    });

    rerender({
      state: baseState,
      transportMode: EDITORIAL_WORKFLOW_TRANSPORT_MODE.POLLING_FALLBACK,
    });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(EDITORIAL_WORKFLOW_POLL_BACKOFF_MS[0]);
    });

    expect(refreshState).toHaveBeenCalled();
  });

  it("returns to SSE mode when the stream reconnects", async () => {
    const { setTransportMode } = renderSseHook();

    await waitFor(() => {
      expect(MockEventSource.instances).toHaveLength(1);
    });

    vi.useFakeTimers();

    await act(async () => {
      MockEventSource.instances[0]?.fail();
      await vi.advanceTimersByTimeAsync(EDITORIAL_WORKFLOW_POLL_BACKOFF_MS[0]);
      MockEventSource.instances.at(-1)?.open();
    });

    expect(setTransportMode).toHaveBeenCalledWith(
      EDITORIAL_WORKFLOW_TRANSPORT_MODE.SSE,
    );
  });

  it("merges progress events into workflow state", async () => {
    const { setState } = renderSseHook();

    await waitFor(() => {
      expect(MockEventSource.instances).toHaveLength(1);
    });

    act(() => {
      MockEventSource.instances[0]?.emit(
        EDITORIAL_WORKFLOW_SSE_EVENTS.PROGRESS,
        {
          event: EDITORIAL_WORKFLOW_SSE_EVENTS.PROGRESS,
          phase: "images",
          current: 2,
          total: 5,
          label: "Generating slide 2 of 5",
        },
      );
    });

    expect(setState).toHaveBeenCalledWith(
      expect.objectContaining({
        phase_progress: expect.objectContaining({ current: 2, total: 5 }),
      }),
    );
  });

  it("tracks phase changes from SSE events", async () => {
    const { setPhaseEvents } = renderSseHook();

    await waitFor(() => {
      expect(MockEventSource.instances).toHaveLength(1);
    });

    act(() => {
      MockEventSource.instances[0]?.emit(
        EDITORIAL_WORKFLOW_SSE_EVENTS.PHASE_CHANGED,
        {
          event: EDITORIAL_WORKFLOW_SSE_EVENTS.PHASE_CHANGED,
          phase: "outline",
          phase_status: WORKFLOW_PHASE_STATUS.IN_PROGRESS,
        },
      );
    });

    expect(setPhaseEvents).toHaveBeenCalled();
  });

  it("ignores non-recoverable SSE errors without a message", async () => {
    const { setError } = renderSseHook();

    await waitFor(() => {
      expect(MockEventSource.instances).toHaveLength(1);
    });

    act(() => {
      MockEventSource.instances[0]?.emit(EDITORIAL_WORKFLOW_SSE_EVENTS.ERROR, {
        event: EDITORIAL_WORKFLOW_SSE_EVENTS.ERROR,
        message: "   ",
        recoverable: false,
      });
    });

    expect(setError).not.toHaveBeenCalled();
  });

  it("does not poll while awaiting human review in fallback mode", async () => {
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
      state: {
        ...baseState,
        phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
        research_findings: [{ title: "Finding" }],
      },
      transportMode: EDITORIAL_WORKFLOW_TRANSPORT_MODE.POLLING_FALLBACK,
    });
  });
});
