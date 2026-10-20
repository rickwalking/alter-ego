/**
 * AE-0440: workflow stream recovery (auth probe, backoff, disconnected state).
 *
 * Feature: tests/features/workflow-stream-recovery-ae0440.feature
 * The stream is a mocked EventSource; the auth probe is the real api-client
 * over a stubbed `fetch`, so a 401 exercises the real session-expired redirect.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import {
  EDITORIAL_WORKFLOW_POLL_BACKOFF_MS,
  EDITORIAL_WORKFLOW_SSE_MAX_RECONNECT_ATTEMPTS,
  EDITORIAL_WORKFLOW_TRANSPORT_MODE,
} from "@/constants/editorial-workflow";
import { WORKFLOW_PHASE_STATUS } from "@/constants/workflow";
import type { EditorialWorkflowState } from "@/modules/editorial";
import { useEditorialWorkflowSse } from "./use-editorial-workflow-sse";

class MockEventSource {
  static instances: MockEventSource[] = [];

  onmessage: ((event: MessageEvent<string>) => void) | null = null;
  onerror: (() => void) | null = null;
  onopen: (() => void) | null = null;

  constructor(public url: string) {
    MockEventSource.instances.push(this);
  }

  addEventListener(): void {}

  close = vi.fn();

  open(): void {
    this.onopen?.();
  }

  fail(): void {
    this.onerror?.();
  }
}

const PAGE_PATH = "/dashboard/create/project-1";
const originalEventSource = globalThis.EventSource;
const originalLocation = globalThis.location;

const runningState: EditorialWorkflowState = {
  project_id: "project-1",
  current_phase: "images",
  phase_status: WORKFLOW_PHASE_STATUS.IN_PROGRESS,
  research_findings: [],
  outline: [],
  slide_drafts: [],
  status: "draft",
};

const probedState: EditorialWorkflowState = {
  ...runningState,
  current_phase: "final_review",
  phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
};

type ProbeReply = { status: number; body?: unknown } | "network-error";

let probeReplies: ProbeReply[] = [];
let lastProbeReply: ProbeReply = { status: 200, body: probedState };
const fetchMock = vi.fn(async (): Promise<Response> => {
  const reply = probeReplies.shift() ?? lastProbeReply;
  if (reply === "network-error") {
    throw new TypeError("Failed to fetch");
  }
  return {
    ok: reply.status >= 200 && reply.status < 300,
    status: reply.status,
    json: async () => reply.body ?? {},
  } as Response;
});

function mockLocation(): { href: string } {
  const location = { href: "", pathname: PAGE_PATH, search: "" };
  Object.defineProperty(globalThis, "location", {
    value: location,
    writable: true,
    configurable: true,
  });
  return location;
}

function setVisibility(state: DocumentVisibilityState): void {
  Object.defineProperty(document, "visibilityState", {
    value: state,
    configurable: true,
  });
}

function renderStream(state: EditorialWorkflowState = runningState) {
  const setState = vi.fn();
  const setPhaseEvents = vi.fn();
  const setTransportMode = vi.fn();
  const refreshState = vi.fn(async () => state);
  const hook = renderHook(() =>
    useEditorialWorkflowSse({
      projectId: "project-1",
      sseEnabled: true,
      state,
      transportMode: EDITORIAL_WORKFLOW_TRANSPORT_MODE.SSE,
      setState,
      setPhaseEvents,
      setTransportMode,
      setError: vi.fn(),
      refreshState,
    }),
  );
  return { ...hook, setState, setTransportMode, refreshState };
}

async function flushProbe(): Promise<void> {
  await act(async () => {
    for (let tick = 0; tick < 25; tick += 1) {
      await Promise.resolve();
    }
  });
}

async function advance(ms: number): Promise<void> {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(ms);
  });
}

function latestStream(): MockEventSource {
  const stream = MockEventSource.instances.at(-1);
  if (!stream) {
    throw new Error("no stream opened");
  }
  return stream;
}

async function failLatestStream(): Promise<void> {
  await act(async () => {
    latestStream().fail();
  });
  await flushProbe();
}

function reconnectDelay(attempt: number): number {
  const index = Math.min(
    attempt,
    EDITORIAL_WORKFLOW_POLL_BACKOFF_MS.length - 1,
  );
  return EDITORIAL_WORKFLOW_POLL_BACKOFF_MS[index];
}

/** Fail the stream and wait out its reconnect delay `budget` times in a row. */
async function spendReconnectBudget(): Promise<void> {
  for (
    let attempt = 0;
    attempt < EDITORIAL_WORKFLOW_SSE_MAX_RECONNECT_ATTEMPTS;
    attempt += 1
  ) {
    await failLatestStream();
    await advance(reconnectDelay(attempt));
  }
}

function disconnectedCalls(setTransportMode: ReturnType<typeof vi.fn>): number {
  return setTransportMode.mock.calls.filter(
    ([mode]) => mode === EDITORIAL_WORKFLOW_TRANSPORT_MODE.DISCONNECTED,
  ).length;
}

beforeEach(() => {
  vi.useFakeTimers();
  MockEventSource.instances = [];
  probeReplies = [];
  lastProbeReply = { status: 200, body: probedState };
  fetchMock.mockClear();
  vi.stubGlobal("fetch", fetchMock);
  // @ts-expect-error — swap in the mock for the duration of each test.
  globalThis.EventSource = MockEventSource;
  setVisibility("visible");
});

afterEach(() => {
  globalThis.EventSource = originalEventSource;
  Object.defineProperty(globalThis, "location", {
    value: originalLocation,
    writable: true,
    configurable: true,
  });
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

describe("AE-0440 workflow stream recovery", () => {
  // Scenario: A dropped stream refetches the state and reconnects
  it("applies the probed state, reconnects after the first delay and refetches on open", async () => {
    const { setState, refreshState } = renderStream();

    await failLatestStream();

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/carousels/project-1/workflow/state",
      expect.objectContaining({ credentials: "include" }),
    );
    expect(setState).toHaveBeenCalledWith(probedState);

    await advance(EDITORIAL_WORKFLOW_POLL_BACKOFF_MS[0] - 1);
    expect(MockEventSource.instances).toHaveLength(1);
    await advance(1);
    expect(MockEventSource.instances).toHaveLength(2);

    refreshState.mockClear();
    await act(async () => {
      latestStream().open();
    });
    expect(refreshState).toHaveBeenCalledTimes(1);
  });

  it("does not refetch when the first stream opens", async () => {
    const { refreshState } = renderStream();

    await act(async () => {
      latestStream().open();
    });

    expect(refreshState).not.toHaveBeenCalled();
  });

  // Scenario: Reconnect delays walk the whole backoff array
  it("waits for each delay of the backoff array, reusing the last one", async () => {
    lastProbeReply = "network-error";
    renderStream();

    const delays = [0, 1, 2, 3].map(reconnectDelay);
    expect(delays).toEqual([5_000, 10_000, 30_000, 30_000]);
    for (const [attempt, delay] of delays.entries()) {
      await failLatestStream();
      await advance(delay - 1);
      expect(MockEventSource.instances).toHaveLength(attempt + 1);
      await advance(1);
      expect(MockEventSource.instances).toHaveLength(attempt + 2);
    }
  });

  // Scenario: A successful reconnect resets the attempt budget
  it("starts again from the first delay after a stream opened", async () => {
    lastProbeReply = "network-error";
    renderStream();

    await failLatestStream();
    await advance(reconnectDelay(0));
    await failLatestStream();
    await advance(reconnectDelay(1));
    await act(async () => {
      latestStream().open();
    });

    await failLatestStream();
    await advance(EDITORIAL_WORKFLOW_POLL_BACKOFF_MS[0]);
    expect(MockEventSource.instances).toHaveLength(4);
  });

  // Scenario: An expired session goes to the session-expired login and stops reconnecting
  it("routes a 401 probe to the session-expired logout and never reconnects", async () => {
    const location = mockLocation();
    lastProbeReply = { status: 401, body: { message: "Session expired" } };
    const { setState, setTransportMode, refreshState } = renderStream();

    await failLatestStream();

    expect(location.href).toBe(
      `/auth/logout?redirect=${encodeURIComponent(PAGE_PATH)}`,
    );
    expect(setState).not.toHaveBeenCalled();
    expect(disconnectedCalls(setTransportMode)).toBe(1);

    await advance(10 * 60_000);
    expect(MockEventSource.instances).toHaveLength(1);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(refreshState).not.toHaveBeenCalled();
  });

  // Scenario: A forbidden probe stops reconnecting
  it("never reconnects after a 403 probe", async () => {
    const location = mockLocation();
    lastProbeReply = { status: 403 };
    renderStream();

    await failLatestStream();
    await advance(10 * 60_000);

    expect(location.href).toBe("/403");
    expect(MockEventSource.instances).toHaveLength(1);
  });

  // Scenario: A workflow that no longer exists stops reconnecting
  it("disconnects after a 404 probe", async () => {
    lastProbeReply = { status: 404 };
    const { setTransportMode } = renderStream();

    await failLatestStream();
    await advance(10 * 60_000);

    expect(MockEventSource.instances).toHaveLength(1);
    expect(disconnectedCalls(setTransportMode)).toBe(1);
  });

  it("keeps backing off when the probe answers a server error", async () => {
    lastProbeReply = { status: 502 };
    renderStream();

    await failLatestStream();
    await advance(EDITORIAL_WORKFLOW_POLL_BACKOFF_MS[0]);

    expect(MockEventSource.instances).toHaveLength(2);
  });

  // Scenario: Live updates disconnect after the reconnect budget is spent
  it("disconnects once the reconnect budget is spent", async () => {
    lastProbeReply = "network-error";
    const { setTransportMode } = renderStream();

    await spendReconnectBudget();
    expect(MockEventSource.instances).toHaveLength(
      EDITORIAL_WORKFLOW_SSE_MAX_RECONNECT_ATTEMPTS + 1,
    );
    expect(disconnectedCalls(setTransportMode)).toBe(0);

    await failLatestStream();
    await advance(10 * 60_000);

    expect(MockEventSource.instances).toHaveLength(
      EDITORIAL_WORKFLOW_SSE_MAX_RECONNECT_ATTEMPTS + 1,
    );
    expect(disconnectedCalls(setTransportMode)).toBe(1);
  });

  // Scenario: Retry reconnects a disconnected stream
  it("reopens the stream with a fresh budget on retry", async () => {
    lastProbeReply = "network-error";
    const { result } = renderStream();
    await spendReconnectBudget();
    await failLatestStream();
    const streamsWhenDisconnected = MockEventSource.instances.length;

    await act(async () => {
      result.current.reconnectLiveUpdates();
    });
    expect(MockEventSource.instances).toHaveLength(streamsWhenDisconnected + 1);

    await failLatestStream();
    await advance(EDITORIAL_WORKFLOW_POLL_BACKOFF_MS[0]);
    expect(MockEventSource.instances).toHaveLength(streamsWhenDisconnected + 2);
  });

  // Scenario: Returning to the tab refetches the state and revives a dead stream
  it("probes and reconnects when the tab becomes visible with a dead stream", async () => {
    lastProbeReply = "network-error";
    const { setState } = renderStream();
    await spendReconnectBudget();
    await failLatestStream();
    const streamsWhenDisconnected = MockEventSource.instances.length;
    lastProbeReply = { status: 200, body: probedState };
    fetchMock.mockClear();

    setVisibility("hidden");
    await act(async () => {
      document.dispatchEvent(new Event("visibilitychange"));
    });
    await flushProbe();
    expect(fetchMock).not.toHaveBeenCalled();

    setVisibility("visible");
    await act(async () => {
      document.dispatchEvent(new Event("visibilitychange"));
    });
    await flushProbe();

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(setState).toHaveBeenCalledWith(probedState);
    expect(MockEventSource.instances).toHaveLength(streamsWhenDisconnected + 1);
  });

  it("does not reconnect from the tab when the probe finds an expired session", async () => {
    lastProbeReply = { status: 404 };
    renderStream();
    await failLatestStream();
    mockLocation();
    lastProbeReply = { status: 401 };

    await act(async () => {
      document.dispatchEvent(new Event("visibilitychange"));
    });
    await flushProbe();

    expect(MockEventSource.instances).toHaveLength(1);
  });

  // Scenario: Returning to the tab with a live stream only refetches the state
  it("only refetches the state when the tab becomes visible with a live stream", async () => {
    const { refreshState } = renderStream();
    await act(async () => {
      latestStream().open();
    });

    await act(async () => {
      document.dispatchEvent(new Event("visibilitychange"));
    });

    expect(refreshState).toHaveBeenCalledTimes(1);
    expect(fetchMock).not.toHaveBeenCalled();
    expect(MockEventSource.instances).toHaveLength(1);
    expect(latestStream().close).not.toHaveBeenCalled();
  });

  // Scenario: Awaiting review state is refreshed even though polling is off
  it("applies the probed state while awaiting human review", async () => {
    const awaiting = {
      ...probedState,
      lock_version: 18,
    } satisfies EditorialWorkflowState;
    lastProbeReply = { status: 200, body: awaiting };
    const { setState } = renderStream(probedState);

    await failLatestStream();

    expect(setState).toHaveBeenCalledWith(awaiting);
  });

  it("drops a probe answered after unmount", async () => {
    let answerProbe: (response: Response) => void = () => {};
    fetchMock.mockImplementationOnce(
      () =>
        new Promise<Response>((resolve) => {
          answerProbe = resolve;
        }),
    );
    const { setState, unmount } = renderStream();

    await act(async () => {
      latestStream().fail();
    });
    unmount();
    answerProbe({
      ok: true,
      status: 200,
      json: async () => probedState,
    } as Response);
    await flushProbe();
    await advance(10 * 60_000);

    expect(setState).not.toHaveBeenCalled();
    expect(MockEventSource.instances).toHaveLength(1);
  });

  it("ignores tab visibility once the stream is disabled", async () => {
    const { unmount, refreshState } = renderStream();
    unmount();

    await act(async () => {
      document.dispatchEvent(new Event("visibilitychange"));
    });

    expect(refreshState).not.toHaveBeenCalled();
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
