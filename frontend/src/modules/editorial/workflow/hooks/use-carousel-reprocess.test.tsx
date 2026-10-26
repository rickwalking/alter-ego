import type { ReactNode } from "react";
import { act, renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { HTTP_METHODS } from "@/constants/api";
import { REPROCESS_POLL_INTERVAL_MS, WORKFLOW_API } from "@/constants/workflow";
import en from "@/i18n/locales/en.json";
import type {
  CarouselReprocessCapability,
  ManualReprocessResponse,
} from "@/schemas/carousel-reprocess";

vi.mock("@/lib/authenticated-fetch", () => ({ authenticatedFetch: vi.fn() }));

import { authenticatedFetch } from "@/lib/authenticated-fetch";
import { useCarouselReprocess } from "./use-carousel-reprocess";

const mockFetch = vi.mocked(authenticatedFetch);
const PROJECT_ID = "project-1";
const PROJECT_URL = WORKFLOW_API.CAROUSEL_REPROCESS(PROJECT_ID);
const labels = en.workflow.reprocess;
let queryClient: QueryClient;

function capability(
  overrides: Partial<CarouselReprocessCapability> = {},
): CarouselReprocessCapability {
  return {
    can_reprocess: true,
    refusal_code: null,
    stuck_kind: "dead_letter",
    run_id: "run-1",
    status: "dead_letter",
    last_phase: "content",
    last_error_code: "run_budget_exhausted",
    position: null,
    eta_seconds: null,
    lock_version: 4,
    ...overrides,
  };
}

function accepted(
  overrides: Partial<ManualReprocessResponse> = {},
): ManualReprocessResponse {
  return {
    outcome: "queued",
    run_id: "run-1",
    status: "queued",
    stuck_kind: "dead_letter",
    position: null,
    eta_seconds: null,
    lock_version: 5,
    worker_notified: true,
    last_error_code: null,
    ...overrides,
  };
}

function reply(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), { status });
}

function wrapper({ children }: { children: ReactNode }): React.ReactElement {
  return (
    <NextIntlClientProvider locale="en" messages={en}>
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    </NextIntlClientProvider>
  );
}

function renderReprocess(refreshWorkflow: () => Promise<unknown>) {
  return renderHook(
    () =>
      useCarouselReprocess({
        projectId: PROJECT_ID,
        enabled: true,
        fallbackExpectedVersion: 4,
        refreshWorkflow,
      }),
    { wrapper },
  );
}

function postCalls(): number {
  return mockFetch.mock.calls.filter(
    ([, options]) => options?.method === HTTP_METHODS.POST,
  ).length;
}

function lastPostBody(): unknown {
  const call = mockFetch.mock.calls.findLast(
    ([, options]) => options?.method === HTTP_METHODS.POST,
  );
  const body = call?.[1]?.body;
  if (typeof body !== "string") throw new Error("Expected a JSON request body");
  return JSON.parse(body) as unknown;
}

function deferred(): {
  promise: Promise<Response>;
  resolve: (response: Response) => void;
} {
  let resolve!: (response: Response) => void;
  const promise = new Promise<Response>((resolvePromise): void => {
    resolve = resolvePromise;
  });
  return { promise, resolve };
}

beforeEach(() => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  mockFetch.mockReset();
  queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: Infinity },
      mutations: { retry: false },
    },
  });
});

afterEach(() => {
  queryClient.clear();
  vi.useRealTimers();
});

describe("useCarouselReprocess", () => {
  /** Scenario: Reprocess shows progress after acceptance */
  it("accepts one run, refreshes workflow, and polls only until terminal", async () => {
    const refreshWorkflow = vi.fn((): Promise<null> => Promise.resolve(null));
    mockFetch.mockResolvedValueOnce(reply(200, capability()));
    const { result } = renderReprocess(refreshWorkflow);
    await waitFor(() =>
      expect(result.current.capability?.status).toBe("dead_letter"),
    );

    mockFetch.mockResolvedValueOnce(
      reply(202, accepted({ position: 2, eta_seconds: 180 })),
    );
    await act(async () => {
      await result.current.reprocess();
    });

    expect(mockFetch).toHaveBeenNthCalledWith(
      2,
      PROJECT_URL,
      expect.objectContaining({ method: HTTP_METHODS.POST }),
    );
    expect(lastPostBody()).toEqual({ expected_version: 4, run_id: "run-1" });
    expect(refreshWorkflow).toHaveBeenCalledTimes(1);
    expect(result.current.capability).toMatchObject({
      status: "queued",
      position: 2,
      eta_seconds: 180,
      lock_version: 5,
    });
    expect(mockFetch).toHaveBeenCalledTimes(2);

    mockFetch.mockResolvedValueOnce(
      reply(200, capability({ status: "running", lock_version: 5 })),
    );
    await act(async () => {
      await vi.advanceTimersByTimeAsync(REPROCESS_POLL_INTERVAL_MS);
    });
    await waitFor(() =>
      expect(result.current.capability?.status).toBe("running"),
    );

    mockFetch.mockResolvedValueOnce(
      reply(200, capability({ status: "dead_letter", lock_version: 5 })),
    );
    await act(async () => {
      await vi.advanceTimersByTimeAsync(REPROCESS_POLL_INTERVAL_MS);
    });
    await waitFor(() =>
      expect(result.current.capability?.status).toBe("dead_letter"),
    );
    const terminalCalls = mockFetch.mock.calls.length;
    await act(async () => {
      await vi.advanceTimersByTimeAsync(REPROCESS_POLL_INTERVAL_MS * 3);
    });
    expect(mockFetch).toHaveBeenCalledTimes(terminalCalls);
  });

  /** Scenario: Rapid clicks cannot duplicate reprocess */
  it("shares one pending request and adopts the existing run response", async () => {
    const refreshWorkflow = vi.fn((): Promise<null> => Promise.resolve(null));
    mockFetch.mockResolvedValueOnce(reply(200, capability()));
    const { result } = renderReprocess(refreshWorkflow);
    await waitFor(() => expect(result.current.canSubmit).toBe(true));
    const pending = deferred();
    mockFetch.mockReturnValueOnce(pending.promise);
    const requests: Promise<void>[] = [];
    await act(async () => {
      requests.push(result.current.reprocess(), result.current.reprocess());
      await Promise.resolve();
    });
    expect(postCalls()).toBe(1);

    await act(async () => {
      pending.resolve(
        reply(200, accepted({ outcome: "existing", run_id: "existing-run" })),
      );
      await Promise.all(requests);
    });
    expect(postCalls()).toBe(1);
    expect(result.current.capability?.run_id).toBe("existing-run");
    expect(refreshWorkflow).toHaveBeenCalledTimes(1);
  });

  /** Scenario: Workspace reprocess errors are translated and safe */
  it("translates stale versions and refreshes the expected version", async () => {
    const refreshWorkflow = vi.fn((): Promise<null> => Promise.resolve(null));
    mockFetch
      .mockResolvedValueOnce(reply(200, capability()))
      .mockResolvedValueOnce(
        reply(409, { detail: "stale_expected_version", raw: "sensitive" }),
      )
      .mockResolvedValueOnce(reply(200, capability({ lock_version: 6 })));
    const { result } = renderReprocess(refreshWorkflow);
    await waitFor(() => expect(result.current.canSubmit).toBe(true));

    await act(async () => {
      await result.current.reprocess();
    });
    expect(result.current.error).toBe(labels.refusals.stale_expected_version);
    expect(result.current.error).not.toContain("sensitive");
    await waitFor(() =>
      expect(result.current.capability?.lock_version).toBe(6),
    );

    mockFetch.mockResolvedValueOnce(reply(202, accepted()));
    await act(async () => {
      await result.current.reprocess();
    });
    expect(lastPostBody()).toEqual({ expected_version: 6, run_id: "run-1" });
  });

  /** Scenario: Workspace reprocess errors are translated and safe */
  it.each([
    [403, labels.errors.forbidden],
    [500, labels.errors.actionFailed],
  ])("shows safe feedback for HTTP %s", async (status, expected) => {
    mockFetch
      .mockResolvedValueOnce(reply(200, capability()))
      .mockResolvedValueOnce(reply(status, { detail: "raw server detail" }));
    const { result } = renderReprocess(
      (): Promise<null> => Promise.resolve(null),
    );
    await waitFor(() => expect(result.current.canSubmit).toBe(true));
    await act(async () => {
      await result.current.reprocess();
    });
    expect(result.current.error).toBe(expected);
    expect(result.current.error).not.toContain("raw server detail");
    expect(result.current.pending).toBe(false);
  });

  /** Scenario: Workspace capability polling stops on forbidden */
  it("clears active progress and stops when a later poll is forbidden", async () => {
    mockFetch
      .mockResolvedValueOnce(reply(200, capability({ status: "queued" })))
      .mockResolvedValueOnce(reply(403, { detail: "sensitive" }));
    const { result } = renderReprocess(
      (): Promise<null> => Promise.resolve(null),
    );
    await waitFor(() =>
      expect(result.current.capability?.status).toBe("queued"),
    );
    await act(async () => {
      await vi.advanceTimersByTimeAsync(REPROCESS_POLL_INTERVAL_MS);
    });
    await waitFor(() => expect(result.current.forbidden).toBe(true));
    expect(result.current.capability).toBeNull();
    expect(result.current.error).toBeNull();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(REPROCESS_POLL_INTERVAL_MS * 3);
    });
    expect(mockFetch).toHaveBeenCalledTimes(2);
  });

  /** Scenario: Workspace capability polling stops on forbidden */
  it("hides forbidden capability feedback and never starts polling", async () => {
    mockFetch.mockResolvedValueOnce(reply(403, { detail: "sensitive" }));
    const { result } = renderReprocess(
      (): Promise<null> => Promise.resolve(null),
    );
    await waitFor(() => expect(result.current.forbidden).toBe(true));
    expect(result.current.capability).toBeNull();
    expect(result.current.error).toBeNull();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(REPROCESS_POLL_INTERVAL_MS * 3);
    });
    expect(mockFetch).toHaveBeenCalledTimes(1);
  });
});
