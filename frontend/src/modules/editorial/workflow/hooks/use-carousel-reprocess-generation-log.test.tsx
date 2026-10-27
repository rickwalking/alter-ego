import type { ReactNode } from "react";
import { act, renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { WORKFLOW_BOARD_POLL_INTERVAL_MS } from "@/constants/workflow";
import en from "@/i18n/locales/en.json";
import type { CarouselReprocessCapability } from "@/schemas/carousel-reprocess";

vi.mock("@/lib/authenticated-fetch", () => ({ authenticatedFetch: vi.fn() }));
vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return { ...actual, apiCall: vi.fn() };
});

import { apiCall } from "@/lib/api-client";
import { authenticatedFetch } from "@/lib/authenticated-fetch";
import { useGenerationLog } from "@/modules/editorial/workspace/hooks/use-generation-log";
import { useCarouselReprocess } from "./use-carousel-reprocess";

const mockFetch = vi.mocked(authenticatedFetch);
const mockApiCall = vi.mocked(apiCall);
const PROJECT_ID = "project-1";
const RUN_ID = "11111111-1111-1111-1111-111111111111";
const EVENT_ID = "22222222-2222-2222-2222-222222222222";
let queryClient: QueryClient;

function reply(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), { status });
}

function capability(status: string): CarouselReprocessCapability {
  return {
    can_reprocess: false,
    refusal_code: null,
    stuck_kind: null,
    run_id: RUN_ID,
    status,
    last_phase: "images",
    last_error_code: null,
    position: null,
    eta_seconds: null,
    lock_version: 4,
  };
}

function logPage(status: string, finishedAt: string | null) {
  return {
    project_id: PROJECT_ID,
    next_cursor: null,
    runs: [
      {
        id: RUN_ID,
        kind: "workflow_resume",
        status,
        queued_at: "2026-10-26T12:00:00Z",
        started_at: "2026-10-26T12:00:01Z",
        finished_at: finishedAt,
        duration_ms: finishedAt === null ? null : 59000,
        attempts: 1,
        error_code: null,
      },
    ],
    events: [
      {
        id: EVENT_ID,
        generation_run_id: RUN_ID,
        event_type: status === "running" ? "run_started" : "run_succeeded",
        phase: null,
        outcome: status === "running" ? "running" : "succeeded",
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

function wrapper({ children }: { children: ReactNode }): React.ReactElement {
  return (
    <NextIntlClientProvider locale="en" messages={en}>
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    </NextIntlClientProvider>
  );
}

beforeEach(() => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  mockFetch.mockReset();
  mockApiCall.mockReset();
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
  vi.unstubAllGlobals();
});

describe("carousel generation log terminal polling", () => {
  /** Scenario: Terminal generation state arrives through existing polling without SSE */
  it("refetches the terminal log through the existing capability poll", async () => {
    const stream = vi.fn();
    vi.stubGlobal("EventSource", stream);
    mockFetch
      .mockResolvedValueOnce(reply(200, capability("running")))
      .mockResolvedValueOnce(reply(200, capability("succeeded")));
    mockApiCall
      .mockResolvedValueOnce(logPage("running", null))
      .mockResolvedValueOnce(logPage("succeeded", "2026-10-26T12:01:00Z"));
    const { result } = renderHook(
      () => {
        const reprocess = useCarouselReprocess({
          projectId: PROJECT_ID,
          enabled: true,
          fallbackExpectedVersion: 4,
          refreshWorkflow: () => Promise.resolve(null),
        });
        const log = useGenerationLog(PROJECT_ID, null);
        return { reprocess, log };
      },
      { wrapper },
    );
    await waitFor(() =>
      expect(result.current.log.data?.pages[0]?.runs[0]?.status).toBe(
        "running",
      ),
    );
    expect(result.current.reprocess.capability?.status).toBe("running");

    await act(async () => {
      await vi.advanceTimersByTimeAsync(WORKFLOW_BOARD_POLL_INTERVAL_MS);
    });

    await waitFor(() =>
      expect(result.current.log.data?.pages[0]?.runs[0]).toMatchObject({
        status: "succeeded",
        finished_at: "2026-10-26T12:01:00Z",
      }),
    );
    expect(mockApiCall).toHaveBeenCalledTimes(2);
    expect(stream).not.toHaveBeenCalled();
    const terminalCalls = mockFetch.mock.calls.length;
    await act(async () => {
      await vi.advanceTimersByTimeAsync(WORKFLOW_BOARD_POLL_INTERVAL_MS * 3);
    });
    expect(mockFetch).toHaveBeenCalledTimes(terminalCalls);
  });
});
