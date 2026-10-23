/**
 * Gherkin: tests/features/dashboard-chat.feature
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createElement, type ReactNode } from "react";

import { REPLY_POLL_INTERVAL_MS } from "../constants";
import { useConversationMessages } from "./use-chat";

vi.mock("@/lib/api-client", () => ({
  apiCall: vi.fn(),
  apiCallNoContent: vi.fn(),
}));

import { apiCall } from "@/lib/api-client";

const mockApiCall = vi.mocked(apiCall);

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: Infinity } },
  });
  return createElement(QueryClientProvider, { client }, children);
}

function historyEndingWith(role: "user" | "assistant") {
  return {
    conversation_id: "conv-1",
    items: [
      {
        id: "m1",
        role,
        content: "QA test",
        sources: [],
        created_at: new Date().toISOString(),
      },
    ],
  };
}

beforeEach(() => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  vi.clearAllMocks();
});

afterEach(() => {
  vi.useRealTimers();
});

describe("useConversationMessages polling", () => {
  /** Scenario: A reply that was still streaming appears after a refresh */
  it("re-reads the history while it ends with an unanswered message", async () => {
    mockApiCall.mockResolvedValue(historyEndingWith("user"));
    const { result } = renderHook(
      () => useConversationMessages("conv-1", true),
      { wrapper },
    );
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockApiCall).toHaveBeenCalledTimes(1);

    await vi.advanceTimersByTimeAsync(REPLY_POLL_INTERVAL_MS);

    await waitFor(() => expect(mockApiCall).toHaveBeenCalledTimes(2));
  });

  /** Scenario: Polling stops when nothing is awaited */
  it("does not re-read once the history ends with a reply", async () => {
    mockApiCall.mockResolvedValue(historyEndingWith("assistant"));
    const { result } = renderHook(
      () => useConversationMessages("conv-1", true),
      { wrapper },
    );
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    await vi.advanceTimersByTimeAsync(REPLY_POLL_INTERVAL_MS * 3);

    expect(mockApiCall).toHaveBeenCalledTimes(1);
  });

  /** Scenario: Polling stops when nothing is awaited */
  it("does not poll unless asked to", async () => {
    mockApiCall.mockResolvedValue(historyEndingWith("user"));
    const { result } = renderHook(() => useConversationMessages("conv-1"), {
      wrapper,
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    await vi.advanceTimersByTimeAsync(REPLY_POLL_INTERVAL_MS * 3);

    expect(mockApiCall).toHaveBeenCalledTimes(1);
  });
});
