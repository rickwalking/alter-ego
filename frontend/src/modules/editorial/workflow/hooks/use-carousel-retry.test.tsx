import type { ReactNode } from "react";
import { act, renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { API_ENDPOINTS, HTTP_METHODS } from "@/constants/api";
import {
  RETRY_KIND,
  RETRY_REFUSAL,
  WORKFLOW_API,
  WORKFLOW_BOARD_POLL_INTERVAL_MS,
  WORKFLOW_PHASE_STATUS,
} from "@/constants/workflow";
import en from "@/i18n/locales/en.json";
import type {
  CarouselRetryAccepted,
  CarouselRetryCapability,
} from "@/schemas/carousel-retry";

vi.mock("@/lib/authenticated-fetch", () => ({ authenticatedFetch: vi.fn() }));

import { authenticatedFetch } from "@/lib/authenticated-fetch";
import { useCarouselRetry } from "./use-carousel-retry";
import type { UseCarouselRetryOptions } from "./types";

const mockFetch = vi.mocked(authenticatedFetch);
const PROJECT_ID = "project-1";
const RETRY_URL = API_ENDPOINTS.CAROUSEL_RETRY(PROJECT_ID);
const labels = en.workflow.retry;
const FAILED_STATE = {
  current_phase: "content",
  phase_status: WORKFLOW_PHASE_STATUS.FAILED,
  lock_version: 7,
};
let queryClient: QueryClient;
let refreshWorkflow: ReturnType<typeof vi.fn<() => Promise<unknown>>>;

function capability(
  overrides: Partial<CarouselRetryCapability> = {},
): CarouselRetryCapability {
  return {
    can_retry: true,
    retry_kind: RETRY_KIND.REDRIVE,
    refusal_code: null,
    lock_version: 7,
    ...overrides,
  };
}

function accepted(
  overrides: Partial<CarouselRetryAccepted> = {},
): CarouselRetryAccepted {
  return {
    accepted: true,
    retry_kind: RETRY_KIND.REDRIVE,
    current_phase: "content",
    phase_status: WORKFLOW_PHASE_STATUS.IN_PROGRESS,
    lock_version: 8,
    autopilot_run_id: null,
    ...overrides,
  };
}

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status });
}

function isPost(init?: RequestInit): boolean {
  return init?.method === HTTP_METHODS.POST;
}

function postCalls(): (typeof mockFetch.mock.calls)[number][] {
  return mockFetch.mock.calls.filter(([, init]) => isPost(init));
}

function reads(url: string): number {
  return mockFetch.mock.calls.filter(
    ([called, init]) => called === url && !isPost(init),
  ).length;
}

function answer(
  read: CarouselRetryCapability | (() => Response),
  post?: () => Response | Promise<Response>,
): void {
  mockFetch.mockImplementation((url, init) => {
    if (isPost(init)) return Promise.resolve(post?.() ?? json(accepted(), 202));
    if (url !== RETRY_URL) return Promise.resolve(json({}));
    return Promise.resolve(typeof read === "function" ? read() : json(read));
  });
}

function wrapper({ children }: { children: ReactNode }): ReactNode {
  return (
    <NextIntlClientProvider locale="en" messages={en}>
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    </NextIntlClientProvider>
  );
}

function options(
  overrides: Partial<UseCarouselRetryOptions> = {},
): UseCarouselRetryOptions {
  return {
    projectId: PROJECT_ID,
    enabled: true,
    workflowState: FAILED_STATE,
    refreshWorkflow,
    ...overrides,
  };
}

function setup(overrides: Partial<UseCarouselRetryOptions> = {}) {
  return renderHook(
    (props: UseCarouselRetryOptions) => useCarouselRetry(props),
    { wrapper, initialProps: options(overrides) },
  );
}

async function ready(overrides: Partial<UseCarouselRetryOptions> = {}) {
  const view = setup(overrides);
  await waitFor(() => expect(view.result.current.canSubmit).toBe(true));
  return view;
}

beforeEach(() => {
  queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  refreshWorkflow = vi.fn<() => Promise<unknown>>().mockResolvedValue(null);
  mockFetch.mockReset();
});

afterEach(() => {
  vi.useRealTimers();
});

describe("useCarouselRetry capability", () => {
  // Scenario: The Retry button shows on a failed card
  it("offers the retry the capability allows", async () => {
    answer(capability());
    const { result } = await ready();
    expect(result.current.visible).toBe(true);
    expect(result.current.capability?.retry_kind).toBe(RETRY_KIND.REDRIVE);
    expect(result.current.toast).toBeNull();
  });

  // Scenario: The Retry button is hidden when the capability refuses
  it("stays hidden when the capability refuses", async () => {
    answer(
      capability({
        can_retry: false,
        retry_kind: null,
        refusal_code: RETRY_REFUSAL.NOT_RETRYABLE,
      }),
    );
    const { result } = setup();
    await waitFor(() => expect(result.current.capability).not.toBeNull());
    expect(result.current.visible).toBe(false);
    expect(result.current.canSubmit).toBe(false);
  });

  // Scenario: The Retry button is hidden when the capability cannot be read
  it.each([403, 404, 500])("stays hidden on a %i read", async (status) => {
    answer(() => json({ detail: "raw server detail" }, status));
    const { result } = setup();
    await waitFor(() => expect(reads(RETRY_URL)).toBe(1));
    await waitFor(() => expect(result.current.capability).toBeNull());
    expect(result.current.visible).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it("does not read the capability while disabled", () => {
    answer(capability());
    setup({ enabled: false });
    expect(mockFetch).not.toHaveBeenCalled();
  });

  // Scenario: Start over still works
  it("stops offering Retry while the workflow restarts", async () => {
    answer(capability());
    const { result, rerender } = await ready();
    rerender(options({ enabled: false }));
    expect(result.current.visible).toBe(false);
    await act(() => result.current.retry());
    expect(postCalls()).toHaveLength(0);
  });

  // Scenario: The capability is read again when the carousel changes
  it("reads the capability again for a new workflow state", async () => {
    answer(capability());
    const { rerender } = await ready();
    expect(reads(RETRY_URL)).toBe(1);
    rerender(options({ workflowState: { ...FAILED_STATE, lock_version: 8 } }));
    await waitFor(() => expect(reads(RETRY_URL)).toBe(2));
  });

  // Scenario: The capability is polled while its refusal is temporary
  it("polls a temporary refusal until the button can appear", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    let refusal: CarouselRetryCapability = capability({
      can_retry: false,
      refusal_code: RETRY_REFUSAL.AUTOPILOT_ACTIVE,
    });
    answer(() => json(refusal));
    const { result } = setup();
    await vi.waitFor(() => expect(result.current.capability).not.toBeNull());
    refusal = capability();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(WORKFLOW_BOARD_POLL_INTERVAL_MS);
    });
    await vi.waitFor(() => expect(result.current.visible).toBe(true));
    const settled = reads(RETRY_URL);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(WORKFLOW_BOARD_POLL_INTERVAL_MS * 2);
    });
    expect(reads(RETRY_URL)).toBe(settled);
  });
});

describe("useCarouselRetry polling", () => {
  // Scenario: The capability is not polled while the phase runs
  it("does not poll a temporary refusal while the phase runs", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const running = {
      ...FAILED_STATE,
      phase_status: WORKFLOW_PHASE_STATUS.IN_PROGRESS,
    };
    answer(
      capability({
        can_retry: false,
        refusal_code: RETRY_REFUSAL.RUN_IN_PROGRESS,
      }),
    );
    const { result, rerender } = setup({ workflowState: running });
    await vi.waitFor(() => expect(result.current.capability).not.toBeNull());
    await act(async () => {
      await vi.advanceTimersByTimeAsync(WORKFLOW_BOARD_POLL_INTERVAL_MS * 2);
    });
    expect(reads(RETRY_URL)).toBe(1);
    rerender(options({ workflowState: FAILED_STATE }));
    await vi.waitFor(() => expect(reads(RETRY_URL)).toBe(2));
  });

  // Scenario: The capability is polled while its refusal is temporary
  it.each([
    RETRY_REFUSAL.RUN_IN_PROGRESS,
    RETRY_REFUSAL.MUTATION_IN_PROGRESS,
    RETRY_REFUSAL.AUTOPILOT_ACTIVE,
  ])("keeps polling %s while the phase is not running", async (code) => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    answer(capability({ can_retry: false, refusal_code: code }));
    const { result } = setup();
    await vi.waitFor(() => expect(result.current.capability).not.toBeNull());
    await act(async () => {
      await vi.advanceTimersByTimeAsync(WORKFLOW_BOARD_POLL_INTERVAL_MS);
    });
    await vi.waitFor(() => expect(reads(RETRY_URL)).toBe(2));
  });
});

describe("useCarouselRetry action", () => {
  // Scenario: A 202 shows the accepted toast
  it("sends one POST at the capability's version and toasts", async () => {
    answer(capability());
    const { result } = await ready();
    await act(() => result.current.retry());
    const posts = postCalls();
    expect(posts).toHaveLength(1);
    expect(posts[0]?.[0]).toBe(RETRY_URL);
    expect(JSON.parse(posts[0]?.[1]?.body as string)).toEqual({
      expected_version: 7,
    });
    expect(result.current.toast?.message).toBe(labels.accepted);
    expect(result.current.toast?.variant).toBe("success");
    expect(refreshWorkflow).toHaveBeenCalledOnce();
    expect(result.current.pending).toBe(false);
  });

  // Scenario: The version falls back to the workflow state
  it("falls back to the workflow state's version", async () => {
    answer(capability({ lock_version: null }));
    const { result } = await ready();
    await act(() => result.current.retry());
    expect(JSON.parse(postCalls()[0]?.[1]?.body as string)).toEqual({
      expected_version: 7,
    });
  });

  // Scenario: Retry stays disabled without a usable version
  it("sends nothing without a usable version", async () => {
    answer(capability({ lock_version: undefined }));
    const { result } = setup({
      workflowState: { ...FAILED_STATE, lock_version: undefined },
    });
    await waitFor(() => expect(result.current.visible).toBe(true));
    expect(result.current.canSubmit).toBe(false);
    await act(() => result.current.retry());
    expect(postCalls()).toHaveLength(0);
  });

  // Scenario: A double click sends one request
  it("sends one request for a double click", async () => {
    const held = Promise.withResolvers<Response>();
    answer(capability(), () => held.promise);
    const { result } = await ready();
    let first: Promise<void> = Promise.resolve();
    act(() => {
      first = result.current.retry();
      void result.current.retry();
    });
    // Scenario: The pending button stays while the request runs
    await waitFor(() => expect(result.current.pending).toBe(true));
    expect(result.current.visible).toBe(true);
    expect(result.current.canSubmit).toBe(false);
    await act(async () => {
      await result.current.retry();
    });
    expect(postCalls()).toHaveLength(1);
    await act(async () => {
      held.resolve(json(accepted(), 202));
      await first;
    });
    expect(result.current.pending).toBe(false);
  });

  // Scenario: A 202 shows the accepted toast
  it("still toasts when the state refresh fails", async () => {
    answer(capability());
    refreshWorkflow.mockRejectedValue(new Error("offline"));
    const { result } = await ready();
    await act(() => result.current.retry());
    expect(result.current.toast?.message).toBe(labels.accepted);
    expect(result.current.error).toBeNull();
  });

  // Scenario: The accepted toast outlives the button
  it("keeps the toast when the capability stops offering Retry", async () => {
    let read = capability();
    answer(() => json(read));
    const { result, rerender } = await ready();
    await act(() => result.current.retry());
    read = capability({
      can_retry: false,
      refusal_code: RETRY_REFUSAL.RUN_IN_PROGRESS,
    });
    rerender(
      options({
        workflowState: {
          ...FAILED_STATE,
          phase_status: WORKFLOW_PHASE_STATUS.IN_PROGRESS,
          lock_version: 8,
        },
      }),
    );
    await waitFor(() =>
      expect(result.current.capability?.can_retry).toBe(false),
    );
    expect(result.current.visible).toBe(false);
    expect(result.current.toast?.message).toBe(labels.accepted);
    act(() => result.current.dismissToast());
    expect(result.current.toast).toBeNull();
  });
});

describe("useCarouselRetry outcome", () => {
  const running = {
    ...FAILED_STATE,
    phase_status: WORKFLOW_PHASE_STATUS.IN_PROGRESS,
    lock_version: 8,
  };

  async function acceptedRun() {
    answer(capability());
    const view = await ready();
    await act(() => view.result.current.retry());
    view.rerender(options({ workflowState: running }));
    return view;
  }

  // Scenario: A finished retry says how it ended
  it("toasts finished-ok when the run stops at a gate", async () => {
    const { result, rerender } = await acceptedRun();
    rerender(
      options({
        workflowState: {
          ...running,
          phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
        },
      }),
    );
    await waitFor(() =>
      expect(result.current.toast?.message).toBe(labels.finishedOk),
    );
    expect(result.current.toast?.variant).toBe("success");
  });

  // Scenario: A failed retry says how it ended
  it.each([WORKFLOW_PHASE_STATUS.FAILED, WORKFLOW_PHASE_STATUS.REJECTED])(
    "toasts finished-failed when the run ends %s",
    async (phaseStatus) => {
      const { result, rerender } = await acceptedRun();
      rerender(
        options({ workflowState: { ...running, phase_status: phaseStatus } }),
      );
      await waitFor(() =>
        expect(result.current.toast?.message).toBe(labels.finishedFailed),
      );
      expect(result.current.toast?.variant).toBe("error");
    },
  );

  // Scenario: A finished retry says how it ended
  it("says nothing for a status that is not an outcome", async () => {
    const { result, rerender } = await acceptedRun();
    rerender(
      options({
        workflowState: {
          ...running,
          phase_status: WORKFLOW_PHASE_STATUS.APPROVED,
        },
      }),
    );
    await waitFor(() => expect(reads(RETRY_URL)).toBeGreaterThan(1));
    expect(result.current.toast?.message).toBe(labels.accepted);
  });

  // Scenario: A finished retry says how it ended
  it("toasts the outcome once", async () => {
    const { result, rerender } = await acceptedRun();
    const gate = {
      ...running,
      phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
    };
    rerender(options({ workflowState: gate }));
    await waitFor(() =>
      expect(result.current.toast?.message).toBe(labels.finishedOk),
    );
    act(() => result.current.dismissToast());
    rerender(options({ workflowState: running }));
    rerender(options({ workflowState: gate }));
    expect(result.current.toast).toBeNull();
  });

  // Scenario: A reopened final review needs no finish toast
  it("tracks no run for a reopened final review", async () => {
    answer(capability({ retry_kind: RETRY_KIND.REOPEN }), () =>
      json(
        accepted({
          retry_kind: RETRY_KIND.REOPEN,
          phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
        }),
        202,
      ),
    );
    const { result, rerender } = await ready();
    await act(() => result.current.retry());
    const gate = {
      ...FAILED_STATE,
      phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
    };
    rerender(options({ workflowState: running }));
    rerender(options({ workflowState: gate }));
    expect(result.current.toast?.message).toBe(labels.accepted);
  });
});

describe("useCarouselRetry run watch", () => {
  const streamed = {
    ...FAILED_STATE,
    phase_status: WORKFLOW_PHASE_STATUS.IN_PROGRESS,
  };
  const running = { ...streamed, lock_version: 8 };
  const atGate = {
    ...running,
    phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
  };

  // Scenario: A retry whose run started before the 202 says how it ended
  it("follows a run the stream showed before the 202", async () => {
    const held = Promise.withResolvers<Response>();
    answer(capability(), () => held.promise);
    const { result, rerender } = await ready();
    let posted: Promise<void> = Promise.resolve();
    act(() => {
      posted = result.current.retry();
    });
    rerender(options({ workflowState: streamed }));
    await act(async () => {
      held.resolve(json(accepted(), 202));
      await posted;
    });
    expect(result.current.toast?.message).toBe(labels.accepted);
    rerender(options({ workflowState: running }));
    expect(result.current.toast?.message).toBe(labels.accepted);
    rerender(options({ workflowState: atGate }));
    await waitFor(() =>
      expect(result.current.toast?.message).toBe(labels.finishedOk),
    );
  });

  // Scenario: A retry whose run started after the 202 says how it ended
  it("follows a run the stream shows after the 202", async () => {
    answer(capability());
    const { result, rerender } = await ready();
    await act(() => result.current.retry());
    rerender(options({ workflowState: { ...FAILED_STATE } }));
    expect(result.current.toast?.message).toBe(labels.accepted);
    rerender(options({ workflowState: streamed }));
    rerender(options({ workflowState: running }));
    expect(result.current.toast?.message).toBe(labels.accepted);
    rerender(
      options({
        workflowState: {
          ...running,
          phase_status: WORKFLOW_PHASE_STATUS.FAILED,
        },
      }),
    );
    await waitFor(() =>
      expect(result.current.toast?.message).toBe(labels.finishedFailed),
    );
  });

  // Scenario: A later run never shows the retry toast
  it("stays quiet for the run after the retry's own", async () => {
    answer(capability());
    const { result, rerender } = await ready();
    await act(() => result.current.retry());
    rerender(options({ workflowState: running }));
    rerender(options({ workflowState: atGate }));
    await waitFor(() =>
      expect(result.current.toast?.message).toBe(labels.finishedOk),
    );
    act(() => result.current.dismissToast());
    rerender(options({ workflowState: { ...running, lock_version: 9 } }));
    rerender(options({ workflowState: { ...atGate, lock_version: 9 } }));
    expect(result.current.toast).toBeNull();
  });

  // Scenario: A later run never shows the retry toast
  it("stops watching when the run ends without an outcome", async () => {
    answer(capability());
    const { result, rerender } = await ready();
    await act(() => result.current.retry());
    rerender(options({ workflowState: running }));
    rerender(
      options({
        workflowState: {
          ...running,
          phase_status: WORKFLOW_PHASE_STATUS.APPROVED,
        },
      }),
    );
    rerender(options({ workflowState: { ...running, lock_version: 9 } }));
    rerender(options({ workflowState: { ...atGate, lock_version: 9 } }));
    expect(result.current.toast?.message).toBe(labels.accepted);
  });

  // Scenario: A refused Retry watches no run
  it("watches nothing after a refusal", async () => {
    answer(capability(), () =>
      json({ detail: RETRY_REFUSAL.RUN_IN_PROGRESS }, 409),
    );
    const { result, rerender } = await ready();
    await act(() => result.current.retry());
    const refused = result.current.toast;
    rerender(options({ workflowState: running }));
    rerender(options({ workflowState: atGate }));
    expect(result.current.toast).toEqual(refused);
  });

  // Scenario: A retry whose state cannot be read again watches no run
  it("watches nothing when the state cannot be read again", async () => {
    answer(capability());
    refreshWorkflow.mockRejectedValue(new Error("offline"));
    const { result, rerender } = await ready();
    await act(() => result.current.retry());
    expect(refreshWorkflow).toHaveBeenCalledTimes(2);
    rerender(options({ workflowState: { ...running, lock_version: 9 } }));
    rerender(options({ workflowState: { ...atGate, lock_version: 9 } }));
    expect(result.current.toast?.message).toBe(labels.accepted);
  });

  // Scenario: A retry whose first state read fails still says how it ended
  it("follows the run when the second read succeeds", async () => {
    answer(capability());
    refreshWorkflow
      .mockRejectedValueOnce(new Error("offline"))
      .mockResolvedValueOnce(null);
    const { result, rerender } = await ready();
    await act(() => result.current.retry());
    expect(refreshWorkflow).toHaveBeenCalledTimes(2);
    rerender(options({ workflowState: running }));
    rerender(options({ workflowState: atGate }));
    await waitFor(() =>
      expect(result.current.toast?.message).toBe(labels.finishedOk),
    );
  });
});

describe("useCarouselRetry refusals", () => {
  // Scenario: A 409 refusal shows its own text
  it.each(Object.values(RETRY_REFUSAL))(
    "shows the text of %s",
    async (code) => {
      answer(capability(), () => json({ detail: code }, 409));
      const { result } = await ready();
      await act(() => result.current.retry());
      expect(result.current.toast?.message).toBe(labels.refusals[code]);
      expect(result.current.toast?.variant).toBe("error");
      expect(result.current.error).toBe(labels.refusals[code]);
      expect(result.current.visible).toBe(true);
    },
  );

  // Scenario: A 409 refusal shows its own text
  it("reads the capability and the state again after a 409", async () => {
    answer(capability(), () =>
      json({ detail: RETRY_REFUSAL.CONCURRENT_UPDATE }, 409),
    );
    const { result } = await ready();
    await act(() => result.current.retry());
    await waitFor(() => expect(reads(RETRY_URL)).toBe(2));
    expect(refreshWorkflow).toHaveBeenCalledOnce();
  });

  // Scenario: A 409 refusal shows its own text
  it("shows a 403 refusal's text without reading again", async () => {
    answer(capability(), () => json({ detail: RETRY_REFUSAL.NOT_OWNER }, 403));
    const { result } = await ready();
    await act(() => result.current.retry());
    expect(result.current.toast?.message).toBe(
      labels.refusals[RETRY_REFUSAL.NOT_OWNER],
    );
    expect(refreshWorkflow).not.toHaveBeenCalled();
    expect(reads(RETRY_URL)).toBe(1);
  });

  // Scenario: A refusal asking for Reprocessar refreshes the Reprocessar control
  it("reads the Reprocessar capability again on use_reprocess", async () => {
    answer(capability(), () =>
      json({ detail: RETRY_REFUSAL.USE_REPROCESS }, 409),
    );
    const invalidate = vi.spyOn(queryClient, "invalidateQueries");
    const { result } = await ready();
    await act(() => result.current.retry());
    expect(invalidate).toHaveBeenCalledWith({
      queryKey: ["carousel-reprocess", PROJECT_ID],
    });
  });

  // Scenario: An untyped failure shows a safe message
  it.each([
    [500, { detail: "stack trace" }],
    [409, { detail: "some_new_code" }],
    [422, { detail: [{ msg: "invalid" }] }],
  ])("shows the safe message for a %i", async (status, body) => {
    answer(capability(), () => json(body, status));
    const { result } = await ready();
    await act(() => result.current.retry());
    expect(result.current.toast?.message).toBe(labels.errors.actionFailed);
    expect(result.current.error).toBe(labels.errors.actionFailed);
  });

  // Scenario: An untyped failure shows a safe message
  it("shows the safe message when the body is not JSON", async () => {
    answer(capability(), () => new Response("<html>", { status: 502 }));
    const { result } = await ready();
    await act(() => result.current.retry());
    expect(result.current.toast?.message).toBe(labels.errors.actionFailed);
  });

  // Scenario: A refusal text clears when the carousel changes
  it("clears the refusal when the workflow state changes", async () => {
    answer(capability(), () =>
      json({ detail: RETRY_REFUSAL.VERSION_CONFLICT }, 409),
    );
    const { result, rerender } = await ready();
    await act(() => result.current.retry());
    expect(result.current.error).not.toBeNull();
    rerender(options({ workflowState: { ...FAILED_STATE, lock_version: 9 } }));
    expect(result.current.error).toBeNull();
  });

  // Scenario: A refusal text clears when the carousel changes
  it("clears the refusal on the next attempt", async () => {
    let refused = true;
    answer(capability(), () =>
      refused
        ? json({ detail: RETRY_REFUSAL.CONCURRENT_UPDATE }, 409)
        : json(accepted(), 202),
    );
    const { result } = await ready();
    await act(() => result.current.retry());
    refused = false;
    await waitFor(() => expect(result.current.canSubmit).toBe(true));
    await act(() => result.current.retry());
    expect(result.current.error).toBeNull();
    expect(result.current.toast?.message).toBe(labels.accepted);
  });
});

describe("the retry endpoint", () => {
  it("lives next to the reprocess endpoint", () => {
    expect(RETRY_URL).toBe(
      WORKFLOW_API.CAROUSEL_REPROCESS(PROJECT_ID).replace("reprocess", "retry"),
    );
  });
});
