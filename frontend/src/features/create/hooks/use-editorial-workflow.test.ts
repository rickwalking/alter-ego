import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { API_ENDPOINTS, HTTP_STATUS } from "@/constants/api";
import { EDITORIAL_REVIEW_ACTIONS } from "@/constants/blog-ai";
import {
  EDITORIAL_WORKFLOW_POLL_BACKOFF_MS,
  EDITORIAL_WORKFLOW_SSE_EVENTS,
  EDITORIAL_WORKFLOW_TRANSPORT_MODE,
} from "@/constants/editorial-workflow";
import { WORKFLOW_PHASE_STATUS } from "@/constants/workflow";
import type { EditorialWorkflowState } from "@/modules/publishing";
import { useEditorialWorkflow } from "./use-editorial-workflow";

vi.mock("@/lib/authenticated-fetch", () => ({
  authenticatedFetch: vi.fn(),
}));

import { authenticatedFetch } from "@/lib/authenticated-fetch";

const mockAuthenticatedFetch = vi.mocked(authenticatedFetch);

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

  removeEventListener(
    type: string,
    listener: (event: MessageEvent<string>) => void,
  ): void {
    const handlers = this.listeners.get(type) ?? [];
    this.listeners.set(
      type,
      handlers.filter((handler) => handler !== listener),
    );
  }

  close = vi.fn(() => {
    this.readyState = MockEventSource.CLOSED;
  });

  emit(type: string, data: unknown): void {
    const event = { data: JSON.stringify(data) } as MessageEvent<string>;
    const handlers = this.listeners.get(type) ?? [];
    handlers.forEach((handler) => handler(event));
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
  lock_version: 1,
};

function mockWorkflowStateResponse(state: EditorialWorkflowState): void {
  mockAuthenticatedFetch.mockResolvedValue({
    ok: true,
    json: async () => state,
  } as Response);
}

function countStateFetches(): number {
  return mockAuthenticatedFetch.mock.calls.filter(
    ([url]) => url === API_ENDPOINTS.CAROUSEL_WORKFLOW_STATE("project-1"),
  ).length;
}

async function advanceResumeWaitTimers(): Promise<void> {
  await vi.advanceTimersByTimeAsync(5_100);
}

beforeEach(() => {
  MockEventSource.instances = [];
  MockEventSource.lastInit = undefined;
  mockAuthenticatedFetch.mockReset();
  mockWorkflowStateResponse(baseState);
  // @ts-expect-error — swap in the mock for the duration of each test.
  globalThis.EventSource = MockEventSource;
});

afterEach(() => {
  globalThis.EventSource = originalEventSource;
  vi.useRealTimers();
  vi.unstubAllEnvs();
});

describe("useEditorialWorkflow", () => {
  // Feature: Unified workflow progress in create workspace
  // Scenario: SSE delivers phase_change without polling during approve
  //   Then the browser should not start a 3 second polling interval for workflow state
  it("does not poll on a fixed interval while loading", async () => {
    let statePolls = 0;
    mockAuthenticatedFetch.mockImplementation(async (url, init) => {
      if (
        url === API_ENDPOINTS.CAROUSEL_WORKFLOW_RESUME("project-1") &&
        init?.method === "POST"
      ) {
        MockEventSource.instances[0]?.emit(
          EDITORIAL_WORKFLOW_SSE_EVENTS.REVIEW_REQUIRED,
          {
            event: EDITORIAL_WORKFLOW_SSE_EVENTS.REVIEW_REQUIRED,
            phase: "outline",
            phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
            gate_payload: {
              current_phase: "outline",
              phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
              research_findings: [{ title: "Finding" }],
              outline: [{ title: "Intro" }],
              slide_drafts: [],
            },
          },
        );
        return {
          ok: true,
          status: HTTP_STATUS.ACCEPTED,
          json: async () => ({
            accepted: true,
            project_id: "project-1",
            current_phase: "research",
            phase_status: WORKFLOW_PHASE_STATUS.IN_PROGRESS,
            lock_version: 2,
          }),
        } as Response;
      }
      if (url === API_ENDPOINTS.CAROUSEL_WORKFLOW_STATE("project-1")) {
        statePolls += 1;
        if (statePolls >= 2) {
          return {
            ok: true,
            json: async () => ({
              ...baseState,
              current_phase: "outline",
              phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
              outline: [{ title: "Intro" }],
            }),
          } as Response;
        }
        return {
          ok: true,
          json: async () => baseState,
        } as Response;
      }
      return {
        ok: true,
        json: async () => baseState,
      } as Response;
    });

    const { result } = renderHook(() => useEditorialWorkflow("project-1"));

    await waitFor(() => {
      expect(result.current.state?.current_phase).toBe("research");
    });

    await waitFor(() => {
      expect(MockEventSource.instances).toHaveLength(1);
    });

    const callsBeforeApprove = countStateFetches();

    await act(async () => {
      await result.current.approve();
    });

    expect(countStateFetches()).toBeLessThanOrEqual(callsBeforeApprove + 1);

    expect(result.current.transportMode).toBe(
      EDITORIAL_WORKFLOW_TRANSPORT_MODE.SSE,
    );
    expect(result.current.state?.current_phase).toBe("outline");
  });

  // Feature: Unified workflow progress in create workspace
  // Scenario: Polling fallback activates only when SSE disconnects
  //   Then the client should poll workflow state as fallback
  //   And polling should use increasing backoff intervals
  it("polls workflow state with backoff when SSE fails", async () => {
    const { result } = renderHook(() => useEditorialWorkflow("project-1"));

    await waitFor(() => {
      expect(MockEventSource.instances).toHaveLength(1);
    });

    vi.useFakeTimers();
    const initialCalls = countStateFetches();

    await act(async () => {
      MockEventSource.instances[0]?.fail();
    });

    expect(result.current.transportMode).toBe(
      EDITORIAL_WORKFLOW_TRANSPORT_MODE.POLLING_FALLBACK,
    );

    await act(async () => {
      await vi.advanceTimersByTimeAsync(EDITORIAL_WORKFLOW_POLL_BACKOFF_MS[0]);
    });

    expect(countStateFetches()).toBeGreaterThan(initialCalls);

    const callsAfterFirstPoll = countStateFetches();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(EDITORIAL_WORKFLOW_POLL_BACKOFF_MS[1]);
    });

    expect(countStateFetches()).toBeGreaterThan(callsAfterFirstPoll);
  });

  // Feature: Unified workflow progress in create workspace
  // Scenario: Polling fallback stops when SSE reconnects
  //   Then interval polling should stop
  //   And the transport mode should return to SSE primary
  it("stops polling fallback when SSE reconnects", async () => {
    const { result } = renderHook(() => useEditorialWorkflow("project-1"));

    await waitFor(() => {
      expect(MockEventSource.instances).toHaveLength(1);
    });

    vi.useFakeTimers();

    await act(async () => {
      MockEventSource.instances[0]?.fail();
    });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(EDITORIAL_WORKFLOW_POLL_BACKOFF_MS[0]);
    });

    const callsAfterFirstPoll = countStateFetches();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(EDITORIAL_WORKFLOW_POLL_BACKOFF_MS[0]);
    });

    const reconnected = MockEventSource.instances.at(-1);
    await act(async () => {
      reconnected?.open();
    });

    expect(result.current.transportMode).toBe(
      EDITORIAL_WORKFLOW_TRANSPORT_MODE.SSE,
    );

    await act(async () => {
      await vi.advanceTimersByTimeAsync(60_000);
    });

    expect(countStateFetches()).toBe(callsAfterFirstPoll);
  });

  // Feature: Unified workflow progress in create workspace
  // Scenario: No progress polling loop at awaiting_human gate
  it("does not poll fallback while awaiting human review", async () => {
    mockWorkflowStateResponse({
      ...baseState,
      phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
    });

    const { result } = renderHook(() => useEditorialWorkflow("project-1"));

    await waitFor(() => {
      expect(result.current.awaitingHumanReview).toBe(true);
    });

    vi.useFakeTimers();

    await act(async () => {
      MockEventSource.instances[0]?.fail();
    });

    expect(result.current.transportMode).toBe(
      EDITORIAL_WORKFLOW_TRANSPORT_MODE.POLLING_FALLBACK,
    );

    const callsBeforeWait = countStateFetches();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(60_000);
    });

    expect(countStateFetches()).toBe(callsBeforeWait);
  });

  // Feature: Unified workflow progress in create workspace
  // Scenario: Mount hydrates workflow state once then opens SSE
  it("hydrates workflow state once on mount and opens one SSE connection", async () => {
    const { result } = renderHook(() => useEditorialWorkflow("project-1"));

    await waitFor(() => {
      expect(MockEventSource.instances).toHaveLength(1);
    });

    expect(countStateFetches()).toBe(1);
    expect(MockEventSource.instances[0]?.url).toBe(
      API_ENDPOINTS.CAROUSEL_WORKFLOW_STREAM("project-1"),
    );
    expect(result.current.transportMode).toBe(
      EDITORIAL_WORKFLOW_TRANSPORT_MODE.SSE,
    );
  });

  // Feature: Unified workflow progress in create workspace
  // Scenario: SSE progress merges nested phase_progress into client state
  it("merges progress events into phase_progress state", async () => {
    const { result } = renderHook(() => useEditorialWorkflow("project-1"));

    await waitFor(() => {
      expect(MockEventSource.instances).toHaveLength(1);
    });

    act(() => {
      MockEventSource.instances[0]?.emit(
        EDITORIAL_WORKFLOW_SSE_EVENTS.PROGRESS,
        {
          event: EDITORIAL_WORKFLOW_SSE_EVENTS.PROGRESS,
          phase: "images",
          phase_progress: {
            current: 4,
            total: 10,
            label: "Generating slide 4 of 10",
          },
        },
      );
    });

    await waitFor(() => {
      expect(result.current.state?.phase_progress).toEqual({
        current: 4,
        total: 10,
        label: "Generating slide 4 of 10",
      });
    });
  });

  it("merges review_required gate payload into workflow state", async () => {
    const { result } = renderHook(() => useEditorialWorkflow("project-1"));

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

    await waitFor(() => {
      expect(result.current.state?.current_phase).toBe("research");
      expect(result.current.state?.research_findings).toHaveLength(1);
    });
  });

  // Feature: Unified workflow progress in create workspace
  // Scenario: SSE delivers phase_change without polling during approve
  it("merges phase changes from SSE events", async () => {
    const { result } = renderHook(() => useEditorialWorkflow("project-1"));

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

    await waitFor(() => {
      expect(result.current.state?.current_phase).toBe("outline");
      expect(result.current.state?.phase_status).toBe(
        WORKFLOW_PHASE_STATUS.IN_PROGRESS,
      );
    });
  });

  it("sends revise action with feedback on revision requests", async () => {
    mockAuthenticatedFetch.mockImplementation(async (url, init) => {
      if (
        url === API_ENDPOINTS.CAROUSEL_WORKFLOW_RESUME("project-1") &&
        init?.method === "POST"
      ) {
        const body = JSON.parse(String(init.body)) as {
          action: string;
          feedback?: string;
        };
        expect(body.action).toBe(EDITORIAL_REVIEW_ACTIONS.REVISE);
        expect(body.feedback).toBe("Prioritize the breach example first");
        return {
          ok: true,
          status: HTTP_STATUS.ACCEPTED,
          json: async () => ({
            accepted: true,
            project_id: "project-1",
            current_phase: "research",
            phase_status: WORKFLOW_PHASE_STATUS.IN_PROGRESS,
            lock_version: 2,
          }),
        } as Response;
      }
      return {
        ok: true,
        json: async () => ({
          ...baseState,
          phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
          research_findings: [{ title: "Finding" }],
        }),
      } as Response;
    });

    const { result } = renderHook(() => useEditorialWorkflow("project-1"));

    await waitFor(() => {
      expect(result.current.state).not.toBeNull();
    });

    await waitFor(() => {
      expect(MockEventSource.instances).toHaveLength(1);
    });

    vi.useFakeTimers();
    await act(async () => {
      const revisePromise = result.current.revise(
        "Prioritize the breach example first",
      );
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
      await vi.advanceTimersByTimeAsync(100);
      await advanceResumeWaitTimers();
      await revisePromise;
    });
    vi.useRealTimers();
  });

  it("sends structured_feedback.target_phase on final review revise", async () => {
    mockAuthenticatedFetch.mockImplementation(async (url, init) => {
      if (
        url === API_ENDPOINTS.CAROUSEL_WORKFLOW_RESUME("project-1") &&
        init?.method === "POST"
      ) {
        const body = JSON.parse(String(init.body)) as {
          structured_feedback?: { target_phase?: string };
        };
        expect(body.structured_feedback?.target_phase).toBe("content");
        return {
          ok: true,
          status: HTTP_STATUS.ACCEPTED,
          json: async () => ({
            accepted: true,
            project_id: "project-1",
            current_phase: "final_review",
            phase_status: WORKFLOW_PHASE_STATUS.IN_PROGRESS,
            lock_version: 2,
          }),
        } as Response;
      }
      return {
        ok: true,
        json: async () => ({
          ...baseState,
          current_phase: "content",
          phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
          outline: [{ title: "Intro" }],
          slide_drafts: [{ draft_text: "Body" }],
        }),
      } as Response;
    });

    const { result } = renderHook(() => useEditorialWorkflow("project-1"));

    await waitFor(() => {
      expect(result.current.state).not.toBeNull();
    });

    await waitFor(() => {
      expect(MockEventSource.instances).toHaveLength(1);
    });

    vi.useFakeTimers();
    await act(async () => {
      const revisePromise = result.current.revise("Rewrite intro", {
        targetPhase: "content",
      });
      MockEventSource.instances[0]?.emit(
        EDITORIAL_WORKFLOW_SSE_EVENTS.REVIEW_REQUIRED,
        {
          event: EDITORIAL_WORKFLOW_SSE_EVENTS.REVIEW_REQUIRED,
          phase: "content",
          phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
          gate_payload: {
            current_phase: "content",
            phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
            research_findings: [],
            outline: [{ title: "Intro" }],
            slide_drafts: [{ draft_text: "Body" }],
          },
        },
      );
      await vi.advanceTimersByTimeAsync(100);
      await advanceResumeWaitTimers();
      await revisePromise;
    });
    vi.useRealTimers();
  });

  it("recovers from resume transport failures by polling workflow state", async () => {
    let resumeCalls = 0;
    let statePolls = 0;
    mockAuthenticatedFetch.mockImplementation(async (url, init) => {
      if (
        url === API_ENDPOINTS.CAROUSEL_WORKFLOW_RESUME("project-1") &&
        init?.method === "POST"
      ) {
        resumeCalls += 1;
        return {
          ok: false,
          status: 500,
          json: async () => ({ detail: "gateway timeout" }),
        } as Response;
      }
      if (url === API_ENDPOINTS.CAROUSEL_WORKFLOW_STATE("project-1")) {
        statePolls += 1;
        if (statePolls >= 3) {
          return {
            ok: true,
            json: async () => ({
              ...baseState,
              current_phase: "outline",
              phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
              outline: [{ title: "Intro" }],
            }),
          } as Response;
        }
        if (statePolls >= 2) {
          return {
            ok: true,
            json: async () => ({
              ...baseState,
              current_phase: "outline",
              phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
              outline: [],
            }),
          } as Response;
        }
        return {
          ok: true,
          json: async () => ({
            ...baseState,
            phase_status: WORKFLOW_PHASE_STATUS.IN_PROGRESS,
          }),
        } as Response;
      }
      return {
        ok: true,
        json: async () => baseState,
      } as Response;
    });

    const { result } = renderHook(() => useEditorialWorkflow("project-1"));

    await waitFor(() => {
      expect(result.current.state).not.toBeNull();
    });

    vi.useFakeTimers();
    try {
      await act(async () => {
        const approvePromise = result.current.approve();
        await vi.runAllTimersAsync();
        await approvePromise;
      });
    } finally {
      vi.useRealTimers();
    }

    expect(resumeCalls).toBe(1);
    expect(result.current.state?.current_phase).toBe("outline");
    expect(result.current.state?.outline).toHaveLength(1);
    expect(result.current.error).toBeNull();
  });

  // Feature: Resume recovery without false errors or manual refresh
  // Scenario: Polling recovery waits for artifacts not only gate status
  it("continues recovery polling until slide drafts exist", async () => {
    let statePolls = 0;
    mockAuthenticatedFetch.mockImplementation(async (url, init) => {
      if (
        url === API_ENDPOINTS.CAROUSEL_WORKFLOW_RESUME("project-1") &&
        init?.method === "POST"
      ) {
        return {
          ok: false,
          status: HTTP_STATUS.INTERNAL_SERVER_ERROR,
          json: async () => ({ detail: "gateway timeout" }),
        } as Response;
      }
      if (url === API_ENDPOINTS.CAROUSEL_WORKFLOW_STATE("project-1")) {
        statePolls += 1;
        if (statePolls >= 3) {
          return {
            ok: true,
            json: async () => ({
              ...baseState,
              current_phase: "content",
              phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
              outline: [{ title: "Intro" }],
              slide_drafts: [{ draft_text: "Body" }],
            }),
          } as Response;
        }
        return {
          ok: true,
          json: async () => ({
            ...baseState,
            current_phase: "content",
            phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
            outline: [{ title: "Intro" }],
            slide_drafts: [],
          }),
        } as Response;
      }
      return {
        ok: true,
        json: async () => ({
          ...baseState,
          phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
        }),
      } as Response;
    });

    const { result } = renderHook(() => useEditorialWorkflow("project-1"));

    await waitFor(() => {
      expect(result.current.state).not.toBeNull();
    });

    vi.useFakeTimers();
    try {
      await act(async () => {
        const approvePromise = result.current.approve();
        await vi.runAllTimersAsync();
        await approvePromise;
      });
    } finally {
      vi.useRealTimers();
    }

    expect(result.current.state?.slide_drafts).toHaveLength(1);
    expect(result.current.error).toBeNull();
  });

  // Feature: Async resume client behavior
  // Scenario: Approve clears loading via SSE not resume HTTP response
  it("accepts async 202 resume and waits for review_required SSE event", async () => {
    mockAuthenticatedFetch.mockImplementation(async (url, init) => {
      if (
        url === API_ENDPOINTS.CAROUSEL_WORKFLOW_RESUME("project-1") &&
        init?.method === "POST"
      ) {
        MockEventSource.instances[0]?.emit(
          EDITORIAL_WORKFLOW_SSE_EVENTS.REVIEW_REQUIRED,
          {
            event: EDITORIAL_WORKFLOW_SSE_EVENTS.REVIEW_REQUIRED,
            phase: "outline",
            phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
            gate_payload: {
              current_phase: "outline",
              phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
              research_findings: [{ title: "Finding" }],
              outline: [{ title: "Intro" }],
              slide_drafts: [],
            },
          },
        );
        return {
          ok: true,
          status: HTTP_STATUS.ACCEPTED,
          json: async () => ({
            accepted: true,
            project_id: "project-1",
            current_phase: "research",
            phase_status: WORKFLOW_PHASE_STATUS.IN_PROGRESS,
            lock_version: 2,
          }),
        } as Response;
      }
      return {
        ok: true,
        json: async () => baseState,
      } as Response;
    });

    const { result } = renderHook(() => useEditorialWorkflow("project-1"));

    await waitFor(() => {
      expect(MockEventSource.instances).toHaveLength(1);
    });

    const statePollsBeforeApprove = countStateFetches();

    await act(async () => {
      await result.current.approve();
    });

    expect(result.current.state?.current_phase).toBe("outline");
    expect(result.current.state?.outline).toHaveLength(1);
    expect(result.current.error).toBeNull();
    expect(countStateFetches() - statePollsBeforeApprove).toBeLessThanOrEqual(
      1,
    );
  });

  // Feature: Resume recovery without false errors or manual refresh
  // Scenario: Artifact SSE hydrates review panel during resume recovery
  it("merges artifact SSE payloads into workflow state", async () => {
    const { result } = renderHook(() => useEditorialWorkflow("project-1"));

    await waitFor(() => {
      expect(MockEventSource.instances).toHaveLength(1);
    });

    act(() => {
      MockEventSource.instances[0]?.emit(
        EDITORIAL_WORKFLOW_SSE_EVENTS.ARTIFACT,
        {
          event: EDITORIAL_WORKFLOW_SSE_EVENTS.ARTIFACT,
          phase: "outline",
          artifact_type: "outline",
          data: [{ title: "Intro" }],
        },
      );
    });

    await waitFor(() => {
      expect(result.current.state?.outline).toEqual([{ title: "Intro" }]);
      expect(result.current.state?.current_phase).toBe("outline");
    });
  });

  // Feature: Resume recovery without false errors or manual refresh
  // Scenario: Loading state persists until expected artifacts exist for the next gate
  it("keeps loading until outline artifacts exist after async approve", async () => {
    mockAuthenticatedFetch.mockImplementation(async (url, init) => {
      if (
        url === API_ENDPOINTS.CAROUSEL_WORKFLOW_RESUME("project-1") &&
        init?.method === "POST"
      ) {
        return {
          ok: true,
          status: HTTP_STATUS.ACCEPTED,
          json: async () => ({
            accepted: true,
            project_id: "project-1",
            current_phase: "research",
            phase_status: WORKFLOW_PHASE_STATUS.IN_PROGRESS,
            lock_version: 2,
          }),
        } as Response;
      }
      return {
        ok: true,
        json: async () => baseState,
      } as Response;
    });

    const { result } = renderHook(() => useEditorialWorkflow("project-1"));

    await waitFor(() => {
      expect(MockEventSource.instances).toHaveLength(1);
    });

    vi.useFakeTimers();
    let approvePromise: Promise<unknown>;
    await act(async () => {
      approvePromise = result.current.approve();
      await vi.advanceTimersByTimeAsync(100);
    });
    expect(result.current.loading).toBe(true);

    await act(async () => {
      MockEventSource.instances[0]?.emit(
        EDITORIAL_WORKFLOW_SSE_EVENTS.REVIEW_REQUIRED,
        {
          event: EDITORIAL_WORKFLOW_SSE_EVENTS.REVIEW_REQUIRED,
          phase: "outline",
          phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
          gate_payload: {
            current_phase: "outline",
            phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
            research_findings: [],
            outline: [{ title: "Intro" }],
            slide_drafts: [],
          },
        },
      );
      await vi.advanceTimersByTimeAsync(100);
      await advanceResumeWaitTimers();
      await approvePromise;
    });
    vi.useRealTimers();

    expect(result.current.loading).toBe(false);
    expect(result.current.state?.outline).toHaveLength(1);
  });

  it("surfaces resume conflict errors without polling recovery", async () => {
    mockAuthenticatedFetch.mockImplementation(async (url, init) => {
      if (
        url === API_ENDPOINTS.CAROUSEL_WORKFLOW_RESUME("project-1") &&
        init?.method === "POST"
      ) {
        return {
          ok: false,
          status: HTTP_STATUS.CONFLICT,
          json: async () => ({ detail: "version_conflict" }),
        } as Response;
      }
      return {
        ok: true,
        json: async () => baseState,
      } as Response;
    });

    const { result } = renderHook(() => useEditorialWorkflow("project-1"));

    await waitFor(() => {
      expect(result.current.state).not.toBeNull();
    });

    const statePollsBeforeApprove = countStateFetches();

    await act(async () => {
      await expect(result.current.approve()).rejects.toThrow();
    });
    await waitFor(() => {
      expect(result.current.error).toBe("version_conflict");
    });
    expect(countStateFetches() - statePollsBeforeApprove).toBe(1);
  });

  it("rejects malformed async resume acceptance payloads", async () => {
    mockAuthenticatedFetch.mockImplementation(async (url, init) => {
      if (
        url === API_ENDPOINTS.CAROUSEL_WORKFLOW_RESUME("project-1") &&
        init?.method === "POST"
      ) {
        return {
          ok: true,
          status: HTTP_STATUS.ACCEPTED,
          json: async () => ({ accepted: false }),
        } as Response;
      }
      return {
        ok: true,
        json: async () => baseState,
      } as Response;
    });

    const { result } = renderHook(() => useEditorialWorkflow("project-1"));

    await waitFor(() => {
      expect(result.current.state).not.toBeNull();
    });

    await act(async () => {
      await expect(result.current.approve()).rejects.toThrow();
    });
    await waitFor(() => {
      expect(result.current.error).toBeTruthy();
    });
  });

  it("falls back to polling when resume fetch throws a network error", async () => {
    let statePolls = 0;
    mockAuthenticatedFetch.mockImplementation(async (url, init) => {
      if (
        url === API_ENDPOINTS.CAROUSEL_WORKFLOW_RESUME("project-1") &&
        init?.method === "POST"
      ) {
        throw new TypeError("Failed to fetch");
      }
      if (url === API_ENDPOINTS.CAROUSEL_WORKFLOW_STATE("project-1")) {
        statePolls += 1;
        if (statePolls >= 2) {
          return {
            ok: true,
            json: async () => ({
              ...baseState,
              current_phase: "outline",
              phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
              outline: [{ title: "Intro" }],
            }),
          } as Response;
        }
        return {
          ok: true,
          json: async () => ({
            ...baseState,
            phase_status: WORKFLOW_PHASE_STATUS.IN_PROGRESS,
          }),
        } as Response;
      }
      return {
        ok: true,
        json: async () => baseState,
      } as Response;
    });

    const { result } = renderHook(() => useEditorialWorkflow("project-1"));

    await waitFor(() => {
      expect(result.current.state).not.toBeNull();
    });

    vi.useFakeTimers();
    try {
      await act(async () => {
        const approvePromise = result.current.approve();
        await vi.runAllTimersAsync();
        await approvePromise;
      });
    } finally {
      vi.useRealTimers();
    }

    expect(statePolls).toBeGreaterThanOrEqual(2);
    expect(result.current.state?.outline).toHaveLength(1);
    expect(result.current.error).toBeNull();
  });

  it("starts workflow via POST and stores returned state", async () => {
    mockAuthenticatedFetch.mockImplementation(async (url, init) => {
      if (
        url === API_ENDPOINTS.CAROUSEL_WORKFLOW_START("project-1") &&
        init?.method === "POST"
      ) {
        return {
          ok: true,
          json: async () => ({
            ...baseState,
            current_phase: "research",
            phase_status: WORKFLOW_PHASE_STATUS.IN_PROGRESS,
          }),
        } as Response;
      }
      return {
        ok: true,
        json: async () => baseState,
      } as Response;
    });

    const { result } = renderHook(() => useEditorialWorkflow("project-1"));

    await waitFor(() => {
      expect(result.current.state).not.toBeNull();
    });

    await act(async () => {
      await result.current.start({
        topic: "Security",
        audience: "Developers",
        brief: "Brief",
        sources: [{ title: "Source", content: "Body" }],
      });
    });

    expect(result.current.state?.current_phase).toBe("research");
    expect(result.current.error).toBeNull();
    expect(result.current.phaseEvents).toEqual(["research"]);
  });

  it("returns null from refreshState when workflow is missing", async () => {
    mockAuthenticatedFetch.mockImplementation(async (url) => {
      if (url === API_ENDPOINTS.CAROUSEL_WORKFLOW_STATE("project-1")) {
        return {
          ok: false,
          status: HTTP_STATUS.NOT_FOUND,
          json: async () => ({ detail: "not found" }),
        } as Response;
      }
      return {
        ok: true,
        json: async () => baseState,
      } as Response;
    });

    const { result } = renderHook(() => useEditorialWorkflow("project-1"));

    await waitFor(() => {
      expect(result.current.state).toBeNull();
    });
  });

  // Regression (c858abd): the workflow/state call must NOT be wrapped in
  // resolveClientApiUrl. The endpoint path already starts with /api, and in
  // production nginx routes /api/* straight to the backend; prefixing it with
  // NEXT_PUBLIC_API_URL produced /api/api/... and a 404. So even when
  // NEXT_PUBLIC_API_URL is set, refresh must use the bare endpoint path.
  it("refreshes workflow state via the bare /api endpoint path (no NEXT_PUBLIC_API_URL prefix)", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_URL", "http://localhost:8000");
    mockAuthenticatedFetch.mockImplementation(async (url) => {
      if (url === API_ENDPOINTS.CAROUSEL_WORKFLOW_STATE("project-1")) {
        return {
          ok: true,
          json: async () => baseState,
        } as Response;
      }
      return {
        ok: true,
        json: async () => baseState,
      } as Response;
    });

    renderHook(() => useEditorialWorkflow("project-1"));

    await waitFor(() => {
      expect(mockAuthenticatedFetch).toHaveBeenCalledWith(
        API_ENDPOINTS.CAROUSEL_WORKFLOW_STATE("project-1"),
      );
    });

    expect(mockAuthenticatedFetch).not.toHaveBeenCalledWith(
      "http://localhost:8000/api/carousels/project-1/workflow/state",
    );
  });

  it("surfaces start failures from the API", async () => {
    mockAuthenticatedFetch.mockImplementation(async (url, init) => {
      if (
        url === API_ENDPOINTS.CAROUSEL_WORKFLOW_START("project-1") &&
        init?.method === "POST"
      ) {
        return {
          ok: false,
          status: 400,
          json: async () => ({ detail: "invalid brief" }),
        } as Response;
      }
      return {
        ok: true,
        json: async () => baseState,
      } as Response;
    });

    const { result } = renderHook(() => useEditorialWorkflow("project-1"));

    await waitFor(() => {
      expect(result.current.state).not.toBeNull();
    });

    let caught: unknown;
    await act(async () => {
      try {
        await result.current.start({
          topic: "Security",
          audience: "Developers",
          brief: "",
          sources: [],
        });
      } catch (error) {
        caught = error;
      }
    });

    expect(caught).toEqual(new Error("invalid brief"));
    await waitFor(() => {
      expect(result.current.error).toBe("invalid brief");
      expect(result.current.loading).toBe(false);
    });
  });

  it("returns null when refresh receives a non-ok response", async () => {
    mockAuthenticatedFetch.mockImplementation(async (url) => {
      if (url === API_ENDPOINTS.CAROUSEL_WORKFLOW_STATE("project-1")) {
        return {
          ok: false,
          status: 500,
          json: async () => ({ detail: "server error" }),
        } as Response;
      }
      return {
        ok: true,
        json: async () => baseState,
      } as Response;
    });

    const { result } = renderHook(() => useEditorialWorkflow("project-1"));

    await waitFor(() => {
      expect(result.current.state).toBeNull();
    });
  });

  it("returns null when refresh throws a network error", async () => {
    mockAuthenticatedFetch.mockImplementation(async (url) => {
      if (url === API_ENDPOINTS.CAROUSEL_WORKFLOW_STATE("project-1")) {
        throw new TypeError("Failed to fetch");
      }
      return {
        ok: true,
        json: async () => baseState,
      } as Response;
    });

    const { result } = renderHook(() => useEditorialWorkflow("project-1"));

    await waitFor(() => {
      expect(result.current.state).toBeNull();
    });
  });

  it("does not append phase events when refreshed state lacks current_phase", async () => {
    mockAuthenticatedFetch.mockResolvedValue({
      ok: true,
      json: async () => ({
        ...baseState,
        current_phase: "",
      }),
    } as Response);

    const { result } = renderHook(() => useEditorialWorkflow("project-1"));

    await waitFor(() => {
      expect(result.current.state?.current_phase).toBe("");
    });
    expect(result.current.phaseEvents).toEqual([]);
  });

  it("reports workflow review flags from hydrated state", async () => {
    mockWorkflowStateResponse({
      ...baseState,
      phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
      research_findings: [{ title: "Finding" }],
    });

    const { result } = renderHook(() => useEditorialWorkflow("project-1"));

    await waitFor(() => {
      expect(result.current.awaitingHumanReview).toBe(true);
      expect(result.current.hasActiveWorkflow).toBe(true);
    });
  });

  it("reports inactive workflow before a phase exists", async () => {
    mockAuthenticatedFetch.mockResolvedValue({
      ok: false,
      status: HTTP_STATUS.NOT_FOUND,
      json: async () => ({ detail: "not found" }),
    } as Response);

    const { result } = renderHook(() => useEditorialWorkflow("project-1"));

    await waitFor(() => {
      expect(result.current.hasActiveWorkflow).toBe(false);
      expect(result.current.awaitingHumanReview).toBe(false);
    });
  });

  it("uses unknown start error messaging for non-Error throws", async () => {
    mockAuthenticatedFetch.mockImplementation(async (url, init) => {
      if (
        url === API_ENDPOINTS.CAROUSEL_WORKFLOW_START("project-1") &&
        init?.method === "POST"
      ) {
        throw "boom";
      }
      return {
        ok: true,
        json: async () => baseState,
      } as Response;
    });

    const { result } = renderHook(() => useEditorialWorkflow("project-1"));

    await waitFor(() => {
      expect(result.current.state).not.toBeNull();
    });

    let caught: unknown;
    await act(async () => {
      try {
        await result.current.start({
          topic: "Security",
          audience: "Developers",
          brief: "Brief",
          sources: [],
        });
      } catch (error) {
        caught = error;
      }
    });

    expect(caught).toBe("boom");
    await waitFor(() => {
      expect(result.current.error).toBe("Workflow start failed");
    });
  });

  it("initializes with loading false and no error", () => {
    const { result } = renderHook(() => useEditorialWorkflow("project-1"));
    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it("does not report awaiting human review while workflow is in progress", async () => {
    mockWorkflowStateResponse({
      ...baseState,
      phase_status: WORKFLOW_PHASE_STATUS.IN_PROGRESS,
    });

    const { result } = renderHook(() => useEditorialWorkflow("project-1"));

    await waitFor(() => {
      expect(result.current.state?.phase_status).toBe(
        WORKFLOW_PHASE_STATUS.IN_PROGRESS,
      );
    });
    expect(result.current.awaitingHumanReview).toBe(false);
  });

  it("refreshState returns null for non-ok responses without parsing JSON", async () => {
    const json = vi.fn(async () => ({ detail: "server error" }));
    mockAuthenticatedFetch.mockImplementation(async (url) => {
      if (url === API_ENDPOINTS.CAROUSEL_WORKFLOW_STATE("project-1")) {
        return {
          ok: false,
          status: HTTP_STATUS.INTERNAL_SERVER_ERROR,
          json,
        } as unknown as Response;
      }
      return {
        ok: true,
        json: async () => baseState,
      } as Response;
    });

    const { result } = renderHook(() => useEditorialWorkflow("project-1"));

    await waitFor(() => {
      expect(result.current.state).toBeNull();
    });

    let refreshed: EditorialWorkflowState | null = baseState;
    await act(async () => {
      refreshed = await result.current.refreshState();
    });

    expect(refreshed).toBeNull();
    expect(json).not.toHaveBeenCalled();
  });

  it("refreshState returns null when the state request throws", async () => {
    mockAuthenticatedFetch.mockImplementation(async (url) => {
      if (url === API_ENDPOINTS.CAROUSEL_WORKFLOW_STATE("project-1")) {
        throw new TypeError("Failed to fetch");
      }
      return {
        ok: true,
        json: async () => baseState,
      } as Response;
    });

    const { result } = renderHook(() => useEditorialWorkflow("project-1"));

    await waitFor(() => {
      expect(result.current.state).toBeNull();
    });

    await act(async () => {
      expect(await result.current.refreshState()).toBeNull();
    });
  });

  it("refreshState appends the current phase to phase events", async () => {
    mockAuthenticatedFetch.mockResolvedValue({
      ok: true,
      json: async () => ({
        ...baseState,
        current_phase: "outline",
      }),
    } as Response);

    const { result } = renderHook(() => useEditorialWorkflow("project-1"));

    await waitFor(() => {
      expect(result.current.phaseEvents).toEqual(["outline"]);
    });

    mockAuthenticatedFetch.mockResolvedValue({
      ok: true,
      json: async () => ({
        ...baseState,
        current_phase: "content",
      }),
    } as Response);

    await act(async () => {
      await result.current.refreshState();
    });

    expect(result.current.phaseEvents).toEqual(["outline", "content"]);
  });

  it("sets loading while start is in flight", async () => {
    let resolveStart: ((value: Response) => void) | undefined;
    const pendingStart = new Promise<Response>((resolve) => {
      resolveStart = resolve;
    });

    mockAuthenticatedFetch.mockImplementation(async (url, init) => {
      if (
        url === API_ENDPOINTS.CAROUSEL_WORKFLOW_START("project-1") &&
        init?.method === "POST"
      ) {
        return pendingStart;
      }
      return {
        ok: true,
        json: async () => baseState,
      } as Response;
    });

    const { result } = renderHook(() => useEditorialWorkflow("project-1"));

    await waitFor(() => {
      expect(result.current.state).not.toBeNull();
    });

    let startPromise: Promise<EditorialWorkflowState> | undefined;
    act(() => {
      startPromise = result.current.start({
        topic: "Security",
        audience: "Developers",
        brief: "Brief",
        sources: [{ title: "Source", content: "Body", source_type: "url" }],
        personaId: "persona-1",
      });
    });

    await waitFor(() => {
      expect(result.current.loading).toBe(true);
    });

    await act(async () => {
      resolveStart?.({
        ok: true,
        json: async () => baseState,
      } as Response);
      await startPromise;
    });

    expect(result.current.loading).toBe(false);
  });

  it("includes persona and source fields in the start payload", async () => {
    mockAuthenticatedFetch.mockImplementation(async (url, init) => {
      if (
        url === API_ENDPOINTS.CAROUSEL_WORKFLOW_START("project-1") &&
        init?.method === "POST"
      ) {
        expect(JSON.parse(String(init.body))).toEqual({
          topic: "Security",
          audience: "Developers",
          brief: "Brief",
          sources: [{ title: "Source", content: "Body", source_type: "url" }],
          persona_id: "persona-1",
        });
        return {
          ok: true,
          json: async () => baseState,
        } as Response;
      }
      return {
        ok: true,
        json: async () => baseState,
      } as Response;
    });

    const { result } = renderHook(() => useEditorialWorkflow("project-1"));

    await waitFor(() => {
      expect(result.current.state).not.toBeNull();
    });

    await act(async () => {
      await result.current.start({
        topic: "Security",
        audience: "Developers",
        brief: "Brief",
        sources: [{ title: "Source", content: "Body", source_type: "url" }],
        personaId: "persona-1",
      });
    });
  });

  it("uses the startFailed fallback when the API omits error detail", async () => {
    mockAuthenticatedFetch.mockImplementation(async (url, init) => {
      if (
        url === API_ENDPOINTS.CAROUSEL_WORKFLOW_START("project-1") &&
        init?.method === "POST"
      ) {
        return {
          ok: false,
          status: HTTP_STATUS.INTERNAL_SERVER_ERROR,
          json: async () => ({}),
        } as Response;
      }
      return {
        ok: true,
        json: async () => baseState,
      } as Response;
    });

    const { result } = renderHook(() => useEditorialWorkflow("project-1"));

    await waitFor(() => {
      expect(result.current.state).not.toBeNull();
    });

    await act(async () => {
      await expect(
        result.current.start({
          topic: "Security",
          audience: "Developers",
          brief: "Brief",
          sources: [],
        }),
      ).rejects.toThrow("Failed to start editorial workflow");
    });

    await waitFor(() => {
      expect(result.current.error).toBe("Failed to start editorial workflow");
    });
  });

  it("does not append phase events when start returns an empty current phase", async () => {
    mockAuthenticatedFetch.mockImplementation(async (url, init) => {
      if (
        url === API_ENDPOINTS.CAROUSEL_WORKFLOW_START("project-1") &&
        init?.method === "POST"
      ) {
        return {
          ok: true,
          json: async () => ({
            ...baseState,
            current_phase: "",
          }),
        } as Response;
      }
      return {
        ok: true,
        json: async () => ({
          ...baseState,
          current_phase: "",
        }),
      } as Response;
    });

    const { result } = renderHook(() => useEditorialWorkflow("project-1"));

    await waitFor(() => {
      expect(result.current.state?.current_phase).toBe("");
    });
    expect(result.current.phaseEvents).toEqual([]);

    await act(async () => {
      await result.current.start({
        topic: "Security",
        audience: "Developers",
        brief: "Brief",
        sources: [],
      });
    });

    expect(result.current.phaseEvents).toEqual([]);
  });

  it("revise wrapper forwards feedback and options to the resume endpoint", async () => {
    mockAuthenticatedFetch.mockImplementation(async (url, init) => {
      if (
        url === API_ENDPOINTS.CAROUSEL_WORKFLOW_RESUME("project-1") &&
        init?.method === "POST"
      ) {
        const body = JSON.parse(String(init.body)) as {
          action: string;
          feedback?: string;
          structured_feedback?: { target_phase?: string; edited_text?: string };
        };
        expect(body.action).toBe(EDITORIAL_REVIEW_ACTIONS.REVISE);
        expect(body.feedback).toBe("Rewrite intro");
        expect(body.structured_feedback).toEqual({
          target_phase: "content",
          edited_text: "Updated body",
        });
        return {
          ok: true,
          status: HTTP_STATUS.OK,
          json: async () => ({
            ...baseState,
            phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
            research_findings: [{ title: "Finding" }],
          }),
        } as Response;
      }
      return {
        ok: true,
        json: async () => baseState,
      } as Response;
    });

    const { result } = renderHook(() => useEditorialWorkflow("project-1"));

    await waitFor(() => {
      expect(result.current.state).not.toBeNull();
    });

    await act(async () => {
      await result.current.revise("Rewrite intro", {
        targetPhase: "content",
        editedText: "Updated body",
      });
    });
  });

  it("refetches workflow state when the project id changes", async () => {
    mockAuthenticatedFetch.mockImplementation(async (url) => {
      if (url === API_ENDPOINTS.CAROUSEL_WORKFLOW_STATE("project-1")) {
        return {
          ok: true,
          json: async () => baseState,
        } as Response;
      }
      if (url === API_ENDPOINTS.CAROUSEL_WORKFLOW_STATE("project-2")) {
        return {
          ok: true,
          json: async () => ({
            ...baseState,
            project_id: "project-2",
            current_phase: "outline",
          }),
        } as Response;
      }
      return {
        ok: true,
        json: async () => baseState,
      } as Response;
    });

    const { result, rerender } = renderHook(
      ({ projectId }: { projectId: string }) => useEditorialWorkflow(projectId),
      { initialProps: { projectId: "project-1" } },
    );

    await waitFor(() => {
      expect(result.current.state?.project_id).toBe("project-1");
    });

    rerender({ projectId: "project-2" });

    await waitFor(() => {
      expect(result.current.state?.project_id).toBe("project-2");
      expect(result.current.state?.current_phase).toBe("outline");
    });
  });

  it("opens SSE with credentials and closes the stream on unmount", async () => {
    const { unmount } = renderHook(() => useEditorialWorkflow("project-1"));

    await waitFor(() => {
      expect(MockEventSource.instances).toHaveLength(1);
    });

    expect(MockEventSource.lastInit).toEqual({ withCredentials: true });

    const source = MockEventSource.instances[0];
    unmount();

    expect(source?.close).toHaveBeenCalled();
  });
});
