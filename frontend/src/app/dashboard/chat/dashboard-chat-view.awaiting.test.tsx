/**
 * Gherkin: tests/features/dashboard-chat.feature
 *
 * The dashboard chat with the real hooks after a refresh mid-reply; only the
 * SSE client and the conversation API are faked.
 */
import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import {
  QueryClient,
  QueryClientProvider,
  infiniteQueryOptions,
  queryOptions,
  skipToken,
} from "@tanstack/react-query";

import { DashboardChatView } from "./dashboard-chat-view";

const mocks = vi.hoisted(() => ({ stream: vi.fn() }));
const NOW = new Date().toISOString();
const CONVERSATION = {
  id: "conv-1",
  title: "Pauta",
  metadata: {},
  created_at: NOW,
  updated_at: NOW,
};

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
  conversationPagesOptions: () =>
    infiniteQueryOptions({
      queryKey: ["conversations", "pages"],
      initialPageParam: 0,
      queryFn: () => ({
        items: [CONVERSATION],
        total: 1,
        limit: 20,
        offset: 0,
      }),
      getNextPageParam: () => undefined,
    }),
  conversationMessagesOptions: (conversationId: string | null) =>
    queryOptions({
      queryKey: ["messages", conversationId],
      queryFn: conversationId
        ? () => [
            {
              id: "m1",
              role: "user",
              content: "QA test",
              sources: [],
              created_at: NOW,
            },
          ]
        : skipToken,
    }),
}));

describe("DashboardChatView while a reply is still being written", () => {
  /** Scenario: Sending waits for the reply the server is still writing */
  it("keeps Send and Enter off until the reply arrives", async () => {
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <QueryClientProvider client={client}>
        <DashboardChatView />
      </QueryClientProvider>,
    );
    await waitFor(() =>
      expect(
        screen.getAllByText("Alter-Ego is typing…").length,
      ).toBeGreaterThan(0),
    );
    const textarea = screen.getByRole("textbox", {
      name: "Message to the Alter-Ego",
    });
    fireEvent.change(textarea, { target: { value: "next question" } });

    expect(screen.getByRole("button", { name: "Send message" })).toBeDisabled();
    fireEvent.keyDown(textarea, { key: "Enter" });
    expect(mocks.stream).not.toHaveBeenCalled();
    expect(textarea).toHaveValue("next question");
  });
});
