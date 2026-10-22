/**
 * Polling fallback of the editorial workflow SSE hook: backoff cap, failed
 * reads and callbacks replaced between renders.
 */

import type { Dispatch, SetStateAction } from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import {
  EDITORIAL_WORKFLOW_POLL_BACKOFF_MS,
  EDITORIAL_WORKFLOW_TRANSPORT_MODE,
  type EditorialWorkflowTransportMode,
} from "@/constants/editorial-workflow";
import { WORKFLOW_PHASE_STATUS } from "@/constants/workflow";
import type { EditorialWorkflowState } from "@/modules/editorial";
import { useEditorialWorkflowSse } from "./use-editorial-workflow-sse";

class IdleEventSource {
  addEventListener = vi.fn();
  close = vi.fn();
}

const runningState: EditorialWorkflowState = {
  project_id: "project-1",
  current_phase: "research",
  phase_status: WORKFLOW_PHASE_STATUS.IN_PROGRESS,
  research_findings: [],
  outline: [],
  slide_drafts: [],
  status: "draft",
};

type RefreshState = () => Promise<EditorialWorkflowState | null>;

type SetTransportMode = Dispatch<
  SetStateAction<EditorialWorkflowTransportMode>
>;

interface PollingProps {
  refreshState: ReturnType<typeof vi.fn<RefreshState>>;
  setTransportMode: ReturnType<typeof vi.fn<SetTransportMode>>;
}

function createProps(
  reply: EditorialWorkflowState | null = runningState,
): PollingProps {
  return {
    refreshState: vi.fn<RefreshState>(() => Promise.resolve(reply)),
    setTransportMode: vi.fn<SetTransportMode>(),
  };
}

function renderPolling(initial: PollingProps) {
  return renderHook(
    (props: PollingProps) =>
      useEditorialWorkflowSse({
        projectId: "project-1",
        sseEnabled: true,
        state: runningState,
        transportMode: EDITORIAL_WORKFLOW_TRANSPORT_MODE.POLLING_FALLBACK,
        setState: vi.fn(),
        setPhaseEvents: vi.fn(),
        setTransportMode: props.setTransportMode,
        setError: vi.fn(),
        refreshState: props.refreshState,
      }),
    { initialProps: initial },
  );
}

async function advance(ms: number): Promise<void> {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(ms);
  });
}

function backoffDelay(attempt: number): number {
  const last = EDITORIAL_WORKFLOW_POLL_BACKOFF_MS.length - 1;
  return EDITORIAL_WORKFLOW_POLL_BACKOFF_MS[Math.min(attempt, last)]!;
}

beforeEach(() => {
  vi.useFakeTimers();
  vi.stubGlobal("EventSource", IdleEventSource);
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

describe("editorial workflow polling fallback", () => {
  // Scenario: Polls keep the last backoff delay once the array is exhausted
  it("keeps polling at the last backoff delay after the array is exhausted", async () => {
    const props = createProps();
    renderPolling(props);
    const attempts = EDITORIAL_WORKFLOW_POLL_BACKOFF_MS.length + 2;

    for (let attempt = 0; attempt < attempts; attempt += 1) {
      await advance(backoffDelay(attempt) - 1);
      expect(props.refreshState).toHaveBeenCalledTimes(attempt);
      await advance(1);
      expect(props.refreshState).toHaveBeenCalledTimes(attempt + 1);
    }
  });

  // Scenario: A failed read ends the polling fallback
  it("returns to SSE when a poll fails to read the state", async () => {
    const props = createProps(null);
    renderPolling(props);

    await advance(backoffDelay(0));

    expect(props.setTransportMode).toHaveBeenCalledWith(
      EDITORIAL_WORKFLOW_TRANSPORT_MODE.SSE,
    );
    await advance(backoffDelay(1));
    expect(props.refreshState).toHaveBeenCalledTimes(1);
  });

  // Scenario: A poll answered after a disconnect does not hide it
  it("keeps the disconnected state when a poll fails after the disconnect", async () => {
    const props = createProps(null);
    const { result } = renderPolling(props);
    result.current.transportModeRef.current =
      EDITORIAL_WORKFLOW_TRANSPORT_MODE.DISCONNECTED;

    await advance(backoffDelay(0));

    expect(props.refreshState).toHaveBeenCalledTimes(1);
    expect(props.setTransportMode).not.toHaveBeenCalled();
  });

  // Scenario: The scheduled poll reads through the latest refreshState
  it("polls through the refreshState of the latest render", async () => {
    const stale = createProps();
    const latest = createProps();
    const { rerender } = renderPolling(stale);
    rerender(latest);

    await advance(backoffDelay(0));

    expect(latest.refreshState).toHaveBeenCalledTimes(1);
    expect(stale.refreshState).not.toHaveBeenCalled();
  });

  // Scenario: The next poll is armed with the latest refreshState
  it("re-arms the next poll with the refreshState of the latest render", async () => {
    const answers: ((state: EditorialWorkflowState) => void)[] = [];
    const stale = createProps();
    stale.refreshState.mockImplementationOnce(
      () =>
        new Promise<EditorialWorkflowState>((resolve) => {
          answers.push(resolve);
        }),
    );
    const latest = createProps();
    const { rerender } = renderPolling(stale);

    await advance(backoffDelay(0));
    rerender(latest);
    await act(() => {
      answers.forEach((answer) => answer(runningState));
      return Promise.resolve();
    });
    await advance(backoffDelay(1));

    expect(stale.refreshState).toHaveBeenCalledTimes(1);
    expect(latest.refreshState).toHaveBeenCalled();
  });
});
