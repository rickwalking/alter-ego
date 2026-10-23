/**
 * Gherkin: tests/features/chat-errors-ui.feature
 *
 * The dashboard chat with the real hooks; only the SSE client and the
 * conversation API are faked.
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import {
  QueryClient,
  QueryClientProvider,
  infiniteQueryOptions,
  queryOptions,
  skipToken,
} from "@tanstack/react-query";

import { SseHttpError } from "@/lib/sse-http-error";
import { DashboardChatView } from "./dashboard-chat-view";

interface StreamOptions {
  body: { content: string };
  onOpen?: () => void;
  onEvent: (event: { event: string; data: Record<string, unknown> }) => void;
  onError?: (error: Error) => void;
  onComplete?: () => void;
}

const mocks = vi.hoisted(() => ({
  stream: vi.fn<(options: StreamOptions) => Promise<void>>(),
  create: vi.fn(),
}));

vi.mock("@/lib/sse-client", () => ({
  streamSseEvents: mocks.stream,
  SSE_EVENT_TYPE: {
    TOKEN: "token",
    COMPLETE: "complete",
    ERROR: "error",
    SOURCES: "sources",
    TOOL_RESULT: "tool_result",
  },
}));

vi.mock("@/modules/conversation/queries", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/modules/conversation/queries")>()),
  createConversation: mocks.create,
  conversationsOptions: () =>
    queryOptions({ queryKey: ["conversations"], queryFn: () => [] }),
  conversationPagesOptions: () =>
    infiniteQueryOptions({
      queryKey: ["conversations", "pages"],
      initialPageParam: 0,
      queryFn: () => ({ items: [], total: 0, limit: 20, offset: 0 }),
      getNextPageParam: () => undefined,
    }),
  conversationMessagesOptions: (conversationId: string | null) =>
    queryOptions({
      queryKey: ["messages", conversationId],
      queryFn: conversationId ? () => [] : skipToken,
    }),
}));

describe("DashboardChatView failures", () => {
  beforeEach(() => {
    mocks.stream.mockReset();
    mocks.create.mockResolvedValue({
      id: "conv-9",
      title: null,
      metadata: {},
      created_at: "2026-10-22T12:00:00Z",
      updated_at: "2026-10-22T12:00:00Z",
    });
  });

  /** Scenario: Retry sends the failed message again */
  it("retries a dashboard send that failed before the server answered", async () => {
    mocks.stream.mockImplementationOnce((options) => {
      options.onError?.(new SseHttpError(502));
      return Promise.resolve();
    });
    mocks.stream.mockImplementationOnce((options) => {
      options.onOpen?.();
      options.onComplete?.();
      return Promise.resolve();
    });
    render(
      <QueryClientProvider client={new QueryClient()}>
        <DashboardChatView />
      </QueryClientProvider>,
    );
    const textbox = screen.getByRole("textbox");
    fireEvent.change(textbox, { target: { value: "draft my week" } });
    await act(async () => {
      fireEvent.keyDown(textbox, { key: "Enter" });
      await Promise.resolve();
    });

    const retry = await screen.findByRole("button", { name: "Try again" });
    await act(async () => {
      fireEvent.click(retry);
      await Promise.resolve();
    });

    await waitFor(() => expect(mocks.stream).toHaveBeenCalledTimes(2));
    expect(mocks.stream.mock.calls[1]![0].body.content).toBe("draft my week");
    expect(textbox).toHaveValue("");
  });
});
