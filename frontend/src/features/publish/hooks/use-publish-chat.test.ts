import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createElement, type ReactNode } from "react";

import {
  PUBLISH_CHAT_STORAGE_KEY,
  CONVERSATION_METADATA_PROJECT_ID,
} from "@/constants/publish-chat";
import { ApiError } from "@/lib/api-client";
import type { Message } from "@/schemas/chat";

// Feature: Publish Page Chat Persistence
// As a carousel author
// I want my chat with the agent to survive page refreshes
// So that the agent retains context across sessions

vi.mock("next/navigation", () => ({
  useParams: vi.fn(),
}));

vi.mock("@tanstack/react-query", async () => {
  const actual = await vi.importActual<typeof import("@tanstack/react-query")>(
    "@tanstack/react-query",
  );
  return {
    ...actual,
    useQueryClient: vi.fn(),
  };
});

vi.mock("@/features/chat/hooks/use-chat", () => ({
  useCreateConversation: vi.fn(),
  useConversationMessages: vi.fn(),
  useConversation: vi.fn(),
  MESSAGES_KEY: "messages",
}));

import { useQueryClient } from "@tanstack/react-query";
import {
  useCreateConversation,
  useConversationMessages,
  useConversation,
} from "@/features/chat/hooks/use-chat";
import { streamSseEvents } from "@/lib/sse-client";
import { usePublishChat } from "./use-publish-chat";

const PROJECT_ID = "test-project-id";

const mockUseCreateConversation = vi.mocked(useCreateConversation);
const mockUseConversationMessages = vi.mocked(useConversationMessages);
const mockUseConversation = vi.mocked(useConversation);
const mockUseQueryClient = vi.mocked(useQueryClient);

class MockWebSocket {
  static instances: MockWebSocket[] = [];
  static OPEN = 1;
  static CLOSED = 3;
  constructor(public url: string) {
    MockWebSocket.instances.push(this);
  }
  send = vi.fn();
  close = vi.fn();
  onopen: (() => void) | null = null;
  onclose: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  onerror: (() => void) | null = null;
  readyState: number = MockWebSocket.OPEN;
}

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return function Wrapper({ children }: { children: ReactNode }) {
    return createElement(
      QueryClientProvider,
      { client: queryClient },
      children,
    );
  };
}

function mockLocalStorage(store: Record<string, string | null> = {}): {
  getItem: typeof localStorage.getItem;
  setItem: typeof localStorage.setItem;
  removeItem: typeof localStorage.removeItem;
} {
  const getItem = vi.fn((key: string) => store[key] ?? null);
  const setItem = vi.fn((key: string, value: string) => {
    store[key] = value;
  });
  const removeItem = vi.fn((key: string) => {
    delete store[key];
  });
  Object.defineProperty(globalThis, "localStorage", {
    value: { getItem, setItem, removeItem },
    writable: true,
    configurable: true,
  });
  return { getItem, setItem, removeItem };
}

function makeHistoryMessage(overrides?: Partial<Message>): Message {
  return {
    id: "msg-1",
    role: "user",
    content: "Hello",
    sources: [],
    created_at: "2026-04-23T00:00:00Z",
    ...overrides,
  };
}

vi.mock("@/lib/sse-client", () => ({
  streamSseEvents: vi.fn(),
  SSE_EVENT_TYPE: {
    TOKEN: "token",
    COMPLETE: "complete",
    ERROR: "error",
    TOOL_RESULT: "tool_result",
  },
}));

beforeEach(() => {
  vi.clearAllMocks();
  mockUseQueryClient.mockReturnValue({
    invalidateQueries: vi.fn(),
  } as unknown as ReturnType<typeof useQueryClient>);

  mockUseCreateConversation.mockReturnValue({
    mutateAsync: vi.fn().mockResolvedValue({ id: "conv-1" }),
    isPending: false,
  } as unknown as ReturnType<typeof useCreateConversation>);

  mockUseConversationMessages.mockReturnValue({
    data: [],
    isLoading: false,
    error: null,
  } as unknown as ReturnType<typeof useConversationMessages>);

  mockUseConversation.mockReturnValue({
    data: undefined,
    isLoading: false,
    error: null,
  } as unknown as ReturnType<typeof useConversation>);
});

describe("usePublishChat (SSE comprehensive)", () => {
  const mockStreamSseEvents = vi.mocked(streamSseEvents);

  beforeEach(() => {
    vi.clearAllMocks();
    mockStreamSseEvents.mockReset();
    mockUseQueryClient.mockReturnValue({
      invalidateQueries: vi.fn(),
    } as unknown as ReturnType<typeof useQueryClient>);
    mockUseCreateConversation.mockReturnValue({
      mutateAsync: vi.fn().mockResolvedValue({ id: "conv-sse" }),
      isPending: false,
    } as unknown as ReturnType<typeof useCreateConversation>);
    mockUseConversationMessages.mockReturnValue({
      data: [],
      error: null,
    } as unknown as ReturnType<typeof useConversationMessages>);
    mockUseConversation.mockReturnValue({
      data: {
        id: "conv-sse",
        metadata: { project_id: PROJECT_ID },
      },
      error: null,
    } as unknown as ReturnType<typeof useConversation>);
    Object.defineProperty(globalThis, "localStorage", {
      value: {
        getItem: vi.fn().mockReturnValue(null),
        setItem: vi.fn(),
        removeItem: vi.fn(),
      },
      writable: true,
      configurable: true,
    });
  });

  // Scenario: Given no stored conv ID, creates new conversation
  it("creates a new conversation when none is stored", async () => {
    const mutateAsync = vi.fn().mockResolvedValue({ id: "conv-new" });
    mockUseCreateConversation.mockReturnValue({
      mutateAsync,
      isPending: false,
    } as unknown as ReturnType<typeof useCreateConversation>);

    renderHook(() => usePublishChat(PROJECT_ID), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(mutateAsync).toHaveBeenCalledTimes(1));
    expect(mutateAsync).toHaveBeenCalledWith({
      title: `Refine: ${PROJECT_ID}`,
      metadata: { [CONVERSATION_METADATA_PROJECT_ID]: PROJECT_ID },
    });
  });

  it("persists a created conversation in localStorage", async () => {
    const { setItem } = mockLocalStorage({});

    const { result } = renderHook(() => usePublishChat(PROJECT_ID), {
      wrapper: createWrapper(),
    });

    await waitFor(() =>
      expect(setItem).toHaveBeenCalledWith(
        PUBLISH_CHAT_STORAGE_KEY(PROJECT_ID),
        "conv-sse",
      ),
    );
    await waitFor(() => expect(result.current.conversationId).toBe("conv-sse"));
  });

  // Scenario: Given a valid stored conv ID, loads history
  it("reads conversation ID from localStorage and loads messages", async () => {
    const store: Record<string, string> = {
      [PUBLISH_CHAT_STORAGE_KEY(PROJECT_ID)]: "conv-stored",
    };
    mockLocalStorage(store);
    mockUseConversation.mockReturnValue({
      data: {
        id: "conv-stored",
        metadata: { project_id: PROJECT_ID },
      },
      error: null,
    } as unknown as ReturnType<typeof useConversation>);

    const history: Message[] = [
      makeHistoryMessage({ id: "h1", role: "user", content: "Hey" }),
      makeHistoryMessage({ id: "h2", role: "assistant", content: "Hi there" }),
    ];
    mockUseConversationMessages.mockReturnValue({
      data: history,
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof useConversationMessages>);

    const { result } = renderHook(() => usePublishChat(PROJECT_ID), {
      wrapper: createWrapper(),
    });

    await waitFor(() =>
      expect(result.current.conversationId).toBe("conv-stored"),
    );
    expect(result.current.messages).toHaveLength(2);
  });

  // Scenario: Given streaming response, calls streamSseEvents with correct args
  it("calls streamSseEvents with the correct endpoint and payload", async () => {
    const { result } = renderHook(() => usePublishChat(PROJECT_ID), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.conversationId).toBe("conv-sse"));

    result.current.sendMessage("Hello");

    await waitFor(() => expect(mockStreamSseEvents).toHaveBeenCalled());
    const callArgs = mockStreamSseEvents.mock.calls[0][0];
    expect(callArgs.url).toContain("/publish-chat/stream");
    expect(callArgs.body).toEqual({
      content: `(carousel project_id=${PROJECT_ID}) Hello`,
    });
  });

  // Scenario: Given tool_result for refine_carousel_copy, invalidates carousel query
  it("invalidates the carousel query on refine_carousel_copy tool result", async () => {
    const invalidateQueries = vi.fn();
    mockUseQueryClient.mockReturnValue({
      invalidateQueries,
    } as unknown as ReturnType<typeof useQueryClient>);

    mockStreamSseEvents.mockImplementation(async ({ onEvent }) => {
      onEvent({ event: "tool_result", data: { tool: "refine_carousel_copy" } });
      onEvent({ event: "complete", data: {} });
    });

    const { result } = renderHook(() => usePublishChat(PROJECT_ID), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.conversationId).toBe("conv-sse"));

    act(() => {
      result.current.sendMessage("refine");
    });

    await waitFor(() =>
      expect(invalidateQueries).toHaveBeenCalledWith({
        queryKey: ["carousel", PROJECT_ID],
      }),
    );
  });

  // Scenario: Given SSE error during stream, sets isStreaming false
  it("sets isStreaming to false when an error event arrives", async () => {
    mockStreamSseEvents.mockImplementation(async ({ onEvent }) => {
      onEvent({ event: "token", data: { content: "Hello" } });
      onEvent({ event: "error", data: { content: "something broke" } });
    });

    const { result } = renderHook(() => usePublishChat(PROJECT_ID), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.conversationId).toBe("conv-sse"));

    act(() => {
      result.current.sendMessage("trigger");
    });

    await waitFor(() => expect(result.current.isStreaming).toBe(false));
  });

  // Scenario: Given rapid re-mounts, only one conversation created
  it("does not create duplicate conversations on rapid mounts", async () => {
    const mutateAsync = vi.fn().mockResolvedValue({ id: "conv-1" });
    mockUseCreateConversation.mockReturnValue({
      mutateAsync,
      isPending: false,
    } as unknown as ReturnType<typeof useCreateConversation>);

    const { rerender } = renderHook(() => usePublishChat(PROJECT_ID), {
      wrapper: createWrapper(),
    });

    rerender();
    rerender();

    await waitFor(() => expect(mutateAsync).toHaveBeenCalledTimes(1));
  });

  // Mutation guard: creation failure does not crash or write localStorage
  it("handles conversation creation failure gracefully", async () => {
    const mutateAsync = vi
      .fn()
      .mockRejectedValue(new ApiError(429, "rate limited"));
    mockUseCreateConversation.mockReturnValue({
      mutateAsync,
      isPending: false,
    } as unknown as ReturnType<typeof useCreateConversation>);

    const { getItem, setItem } = mockLocalStorage({});

    renderHook(() => usePublishChat(PROJECT_ID), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(mutateAsync).toHaveBeenCalled());
    expect(setItem).not.toHaveBeenCalled();
    expect(getItem).toHaveBeenCalledWith(PUBLISH_CHAT_STORAGE_KEY(PROJECT_ID));
  });

  it("replaces a stored conversation that no longer exists", async () => {
    const mutateAsync = vi.fn().mockResolvedValue({ id: "conv-replacement" });
    mockUseCreateConversation.mockReturnValue({
      mutateAsync,
      isPending: false,
    } as unknown as ReturnType<typeof useCreateConversation>);
    const { removeItem, setItem } = mockLocalStorage({
      [PUBLISH_CHAT_STORAGE_KEY(PROJECT_ID)]: "conv-stale",
    });
    mockUseConversationMessages.mockImplementation(
      (conversationId: string | null) =>
        ({
          data: [],
          isLoading: false,
          error:
            conversationId === "conv-stale"
              ? new ApiError(404, "not found")
              : null,
        }) as unknown as ReturnType<typeof useConversationMessages>,
    );

    renderHook(() => usePublishChat(PROJECT_ID), {
      wrapper: createWrapper(),
    });

    await waitFor(() =>
      expect(removeItem).toHaveBeenCalledWith(
        PUBLISH_CHAT_STORAGE_KEY(PROJECT_ID),
      ),
    );
    await waitFor(() => expect(mutateAsync).toHaveBeenCalledTimes(1));
    await waitFor(() =>
      expect(setItem).toHaveBeenCalledWith(
        PUBLISH_CHAT_STORAGE_KEY(PROJECT_ID),
        "conv-replacement",
      ),
    );
  });

  it("replaces a stored conversation that belongs to another project", async () => {
    const mutateAsync = vi.fn().mockResolvedValue({ id: "conv-replacement" });
    mockUseCreateConversation.mockReturnValue({
      mutateAsync,
      isPending: false,
    } as unknown as ReturnType<typeof useCreateConversation>);
    const { removeItem } = mockLocalStorage({
      [PUBLISH_CHAT_STORAGE_KEY(PROJECT_ID)]: "conv-other-project",
    });
    mockUseConversation.mockImplementation(
      (conversationId: string | null) =>
        ({
          data:
            conversationId === "conv-other-project"
              ? {
                  id: "conv-other-project",
                  title: "Other",
                  metadata: {
                    [CONVERSATION_METADATA_PROJECT_ID]: "other-project",
                  },
                  created_at: "2026-04-23T00:00:00Z",
                  updated_at: "2026-04-23T00:00:00Z",
                }
              : undefined,
          isLoading: false,
          error: null,
        }) as unknown as ReturnType<typeof useConversation>,
    );

    renderHook(() => usePublishChat(PROJECT_ID), {
      wrapper: createWrapper(),
    });

    await waitFor(() =>
      expect(removeItem).toHaveBeenCalledWith(
        PUBLISH_CHAT_STORAGE_KEY(PROJECT_ID),
      ),
    );
    await waitFor(() => expect(mutateAsync).toHaveBeenCalledTimes(1));
  });

  // Edge case: sendMessage while already streaming does nothing
  it("does not send a message when already streaming", async () => {
    mockStreamSseEvents.mockImplementation(async () => {
      await new Promise((r) => setTimeout(r, 100));
    });

    const { result } = renderHook(() => usePublishChat(PROJECT_ID), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.conversationId).toBe("conv-sse"));

    act(() => {
      result.current.sendMessage("first");
    });
    expect(result.current.isStreaming).toBe(true);

    // Second send while streaming should not call streamSseEvents again
    const callCount = mockStreamSseEvents.mock.calls.length;
    act(() => {
      result.current.sendMessage("second");
    });
    expect(mockStreamSseEvents.mock.calls.length).toBe(callCount);
  });

  // Edge case: empty sendMessage does nothing
  it("does not send an empty or whitespace-only message", async () => {
    const { result } = renderHook(() => usePublishChat(PROJECT_ID), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.conversationId).toBe("conv-sse"));

    act(() => {
      result.current.sendMessage("   ");
    });

    expect(mockStreamSseEvents).not.toHaveBeenCalled();
    expect(result.current.isStreaming).toBe(false);
  });

  // Mutation-killing: guard clause prevents duplicate creation
  it("does not create a conversation when conversationId already exists", async () => {
    const mutateAsync = vi.fn().mockResolvedValue({ id: "conv-new" });
    mockUseCreateConversation.mockReturnValue({
      mutateAsync,
      isPending: false,
    } as unknown as ReturnType<typeof useCreateConversation>);

    // Seed localStorage so the hook starts with a conversationId
    const store: Record<string, string> = {
      [PUBLISH_CHAT_STORAGE_KEY(PROJECT_ID)]: "conv-existing",
    };
    mockLocalStorage(store);
    mockUseConversation.mockReturnValue({
      data: {
        id: "conv-existing",
        metadata: { project_id: PROJECT_ID },
      },
      error: null,
    } as unknown as ReturnType<typeof useConversation>);

    renderHook(() => usePublishChat(PROJECT_ID), {
      wrapper: createWrapper(),
    });

    // Wait a tick to ensure the layout effect has run
    await new Promise((resolve) => setTimeout(resolve, 10));
    expect(mutateAsync).not.toHaveBeenCalled();
  });

  // Mutation-killing: sendMessage trims whitespace and appends to messages
  it("trims whitespace from outgoing messages and appends them", async () => {
    const { result } = renderHook(() => usePublishChat(PROJECT_ID), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.conversationId).toBe("conv-sse"));

    act(() => {
      result.current.sendMessage("  hello world  ");
    });

    await waitFor(() => expect(mockStreamSseEvents).toHaveBeenCalled());

    const callArgs = mockStreamSseEvents.mock.calls[0][0];
    expect(callArgs.body.content).toBe(
      `(carousel project_id=${PROJECT_ID}) hello world`,
    );
    expect(result.current.messages).toHaveLength(1);
    expect(result.current.messages[0]?.content).toBe("hello world");
  });

  // Mutation-killing: COMPLETE message stops streaming
  it("stops streaming when a complete message arrives", async () => {
    mockStreamSseEvents.mockImplementation(async ({ onEvent }) => {
      onEvent({ event: "token", data: { content: "Hello" } });
      onEvent({ event: "complete", data: {} });
    });

    const { result } = renderHook(() => usePublishChat(PROJECT_ID), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.conversationId).toBe("conv-sse"));

    act(() => {
      result.current.sendMessage("go");
    });

    await waitFor(() => expect(result.current.isStreaming).toBe(false));
  });

  it("starts a fresh assistant message after complete resets stream state", async () => {
    mockStreamSseEvents.mockImplementation(({ onEvent }) => {
      onEvent({ event: "token", data: { content: "old" } });
      onEvent({ event: "complete", data: {} });
      return Promise.resolve();
    });

    const { result } = renderHook(() => usePublishChat(PROJECT_ID), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.conversationId).toBe("conv-sse"));

    result.current.sendMessage("first");
    await waitFor(() => expect(mockStreamSseEvents).toHaveBeenCalledTimes(1));

    // Simulate a second message
    mockStreamSseEvents.mockClear();
    result.current.sendMessage("second");
    await waitFor(() => expect(mockStreamSseEvents).toHaveBeenCalledTimes(1));
  });

  it("stops streaming after an error event", async () => {
    mockStreamSseEvents.mockImplementation(({ onEvent }) => {
      onEvent({ event: "token", data: { content: "old" } });
      onEvent({ event: "error", data: { content: "failed" } });
      return Promise.resolve();
    });

    const { result } = renderHook(() => usePublishChat(PROJECT_ID), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.conversationId).toBe("conv-sse"));

    result.current.sendMessage("first");
    await waitFor(() => expect(result.current.isStreaming).toBe(false));
    expect(mockStreamSseEvents).toHaveBeenCalledTimes(1);
  });

  // Mutation-killing: onComplete clears streaming state
  it("clears streaming state when the stream completes", async () => {
    mockStreamSseEvents.mockImplementation(({ onEvent }) => {
      onEvent({ event: "token", data: { content: "msg" } });
      onEvent({ event: "complete", data: {} });
      return Promise.resolve();
    });

    const { result } = renderHook(() => usePublishChat(PROJECT_ID), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.conversationId).toBe("conv-sse"));
    expect(result.current.isStreaming).toBe(false);

    result.current.sendMessage("test");
    await waitFor(() => expect(mockStreamSseEvents).toHaveBeenCalled());
    await waitFor(() => expect(result.current.isStreaming).toBe(false));
  });

  // Mutation-killing: non-refine_carousel_copy tool results do not invalidate
  it("does not invalidate carousel query for unrelated tool results", async () => {
    const invalidateQueries = vi.fn();
    mockUseQueryClient.mockReturnValue({
      invalidateQueries,
    } as unknown as ReturnType<typeof useQueryClient>);

    mockStreamSseEvents.mockImplementation(async ({ onEvent }) => {
      onEvent({ event: "tool_result", data: { tool: "some_other_tool" } });
      onEvent({ event: "complete", data: {} });
    });

    const { result } = renderHook(() => usePublishChat(PROJECT_ID), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.conversationId).toBe("conv-sse"));

    act(() => {
      result.current.sendMessage("test");
    });

    await waitFor(() => expect(result.current.isStreaming).toBe(false));
    expect(invalidateQueries).not.toHaveBeenCalled();
  });
});
