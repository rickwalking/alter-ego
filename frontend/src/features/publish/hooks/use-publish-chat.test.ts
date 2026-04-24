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
    return createElement(QueryClientProvider, { client: queryClient }, children);
  };
}

function mockLocalStorage(
  store: Record<string, string | null> = {},
): {
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

beforeEach(() => {
  vi.clearAllMocks();
  MockWebSocket.instances = [];
  Object.defineProperty(globalThis, "WebSocket", {
    value: Object.assign(MockWebSocket, {
      OPEN: MockWebSocket.OPEN,
      CLOSED: MockWebSocket.CLOSED,
    }) as unknown as typeof WebSocket,
    writable: true,
    configurable: true,
  });
  Object.defineProperty(globalThis, "localStorage", {
    value: {
      getItem: vi.fn().mockReturnValue(null),
      setItem: vi.fn(),
      removeItem: vi.fn(),
    },
    writable: true,
    configurable: true,
  });

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

  Object.defineProperty(window, "location", {
    value: { protocol: "http:", host: "localhost" },
    writable: true,
    configurable: true,
  });
});

afterEach(() => {
  Object.defineProperty(globalThis, "WebSocket", {
    value: undefined,
    writable: true,
    configurable: true,
  });
});

describe("usePublishChat", () => {
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

  it("persists a created conversation and connects a project-scoped WebSocket", async () => {
    const mutateAsync = vi.fn().mockResolvedValue({ id: "conv-new" });
    mockUseCreateConversation.mockReturnValue({
      mutateAsync,
      isPending: false,
    } as unknown as ReturnType<typeof useCreateConversation>);
    const { setItem } = mockLocalStorage({});

    const { result } = renderHook(() => usePublishChat(PROJECT_ID), {
      wrapper: createWrapper(),
    });

    await waitFor(() =>
      expect(setItem).toHaveBeenCalledWith(
        PUBLISH_CHAT_STORAGE_KEY(PROJECT_ID),
        "conv-new",
      ),
    );
    await waitFor(() => expect(result.current.conversationId).toBe("conv-new"));
    await waitFor(() => expect(MockWebSocket.instances).toHaveLength(1));
    expect(MockWebSocket.instances[0].url).toBe(
      "ws://localhost/ws/chat/conv-new",
    );
  });

  // Scenario: Given a valid stored conv ID, loads history
  it("reads conversation ID from localStorage and loads messages", () => {
    const store: Record<string, string> = {
      [PUBLISH_CHAT_STORAGE_KEY(PROJECT_ID)]: "conv-stored",
    };
    mockLocalStorage(store);

    const history: Message[] = [
      makeHistoryMessage({ id: "h1", role: "user", content: "Hey" }),
      makeHistoryMessage({
        id: "h2",
        role: "assistant",
        content: "Hi there",
      }),
    ];
    mockUseConversationMessages.mockReturnValue({
      data: history,
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof useConversationMessages>);

    const { result } = renderHook(() => usePublishChat(PROJECT_ID), {
      wrapper: createWrapper(),
    });

    const ws = MockWebSocket.instances[0];
    expect(ws).toBeDefined();

    act(() => {
      result.current.sendMessage("shorten caption");
    });

    expect(ws.send).toHaveBeenCalledWith(
      JSON.stringify({
        content: `(carousel project_id=${PROJECT_ID}) shorten caption`,
      }),
    );
    expect(result.current.isStreaming).toBe(true);
  });

  it("uses secure WebSocket protocol on HTTPS pages", () => {
    Object.defineProperty(window, "location", {
      value: { protocol: "https:", host: "example.test" },
      writable: true,
      configurable: true,
    });
    mockLocalStorage({
      [PUBLISH_CHAT_STORAGE_KEY(PROJECT_ID)]: "conv-secure",
    });

    renderHook(() => usePublishChat(PROJECT_ID), {
      wrapper: createWrapper(),
    });

    expect(MockWebSocket.instances[0].url).toBe(
      "wss://example.test/ws/chat/conv-secure",
    );
  });

  // Scenario: Given streaming response, updates assistant message in-place
  it("updates the last assistant message while streaming tokens", async () => {
    const store: Record<string, string> = {
      [PUBLISH_CHAT_STORAGE_KEY(PROJECT_ID)]: "conv-1",
    };
    mockLocalStorage(store);

    mockUseConversationMessages.mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof useConversationMessages>);

    const { result } = renderHook(() => usePublishChat(PROJECT_ID), {
      wrapper: createWrapper(),
    });

    const ws = MockWebSocket.instances[0];
    expect(ws).toBeDefined();

    act(() => {
      ws.onmessage?.({
        data: JSON.stringify({ type: "token", content: "Hello" }),
      });
    });
    await waitFor(() => expect(result.current.messages).toHaveLength(1));
    expect(result.current.messages[0]?.content).toBe("Hello");

    act(() => {
      ws.onmessage?.({
        data: JSON.stringify({ type: "token", content: " world" }),
      });
    });
    await waitFor(() =>
      expect(result.current.messages[0]?.content).toBe("Hello world"),
    );
  });

  // Scenario: Given tool_result for refine_carousel_copy, invalidates carousel query
  it("invalidates the carousel query on refine_carousel_copy tool result", () => {
    const invalidateQueries = vi.fn();
    mockUseQueryClient.mockReturnValue({
      invalidateQueries,
    } as unknown as ReturnType<typeof useQueryClient>);

    const store: Record<string, string> = {
      [PUBLISH_CHAT_STORAGE_KEY(PROJECT_ID)]: "conv-1",
    };
    mockLocalStorage(store);

    mockUseConversationMessages.mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof useConversationMessages>);

    renderHook(() => usePublishChat(PROJECT_ID), {
      wrapper: createWrapper(),
    });

    const ws = MockWebSocket.instances[0];
    expect(ws).toBeDefined();

    act(() => {
      ws.onmessage?.({
        data: JSON.stringify({
          type: "tool_result",
          tool: "refine_carousel_copy",
        }),
      });
    });

    expect(invalidateQueries).toHaveBeenCalledWith({
      queryKey: ["carousel", PROJECT_ID],
    });
  });

  // Scenario: Given WebSocket disconnect during stream, sets isStreaming false
  it("sets isStreaming to false when the WebSocket closes", async () => {
    const store: Record<string, string> = {
      [PUBLISH_CHAT_STORAGE_KEY(PROJECT_ID)]: "conv-1",
    };
    mockLocalStorage(store);

    mockUseConversationMessages.mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof useConversationMessages>);

    const { result } = renderHook(() => usePublishChat(PROJECT_ID), {
      wrapper: createWrapper(),
    });

    const ws = MockWebSocket.instances[0];
    expect(ws).toBeDefined();

    act(() => {
      result.current.sendMessage("trigger stream");
    });
    expect(result.current.isStreaming).toBe(true);

    act(() => {
      ws.onclose?.();
    });
    await waitFor(() => expect(result.current.isStreaming).toBe(false));
  });

  it("closes the WebSocket on unmount", () => {
    mockLocalStorage({
      [PUBLISH_CHAT_STORAGE_KEY(PROJECT_ID)]: "conv-1",
    });

    const { unmount } = renderHook(() => usePublishChat(PROJECT_ID), {
      wrapper: createWrapper(),
    });

    const ws = MockWebSocket.instances[0];
    unmount();
    expect(ws.close).toHaveBeenCalledTimes(1);
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
    expect(getItem).toHaveBeenCalledWith(
      PUBLISH_CHAT_STORAGE_KEY(PROJECT_ID),
    );
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
    mockUseConversationMessages.mockImplementation((conversationId) => ({
      data: [],
      isLoading: false,
      error:
        conversationId === "conv-stale"
          ? new ApiError(404, "not found")
          : null,
    } as unknown as ReturnType<typeof useConversationMessages>));

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
    mockUseConversation.mockImplementation((conversationId) => ({
      data:
        conversationId === "conv-other-project"
          ? {
              id: "conv-other-project",
              title: "Other",
              metadata: { [CONVERSATION_METADATA_PROJECT_ID]: "other-project" },
              created_at: "2026-04-23T00:00:00Z",
              updated_at: "2026-04-23T00:00:00Z",
            }
          : undefined,
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof useConversation>));

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

  // Edge case: sendMessage with closed WebSocket does nothing
  it("does not send a message when the WebSocket is not open", () => {
    const store: Record<string, string> = {
      [PUBLISH_CHAT_STORAGE_KEY(PROJECT_ID)]: "conv-1",
    };
    mockLocalStorage(store);

    mockUseConversationMessages.mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof useConversationMessages>);

    const { result } = renderHook(() => usePublishChat(PROJECT_ID), {
      wrapper: createWrapper(),
    });

    const ws = MockWebSocket.instances[0];
    ws.readyState = WebSocket.CLOSED;

    result.current.sendMessage("test");

    expect(ws.send).not.toHaveBeenCalled();
    expect(result.current.isStreaming).toBe(false);
  });

  // Edge case: empty sendMessage does nothing
  it("does not send an empty or whitespace-only message", () => {
    const store: Record<string, string> = {
      [PUBLISH_CHAT_STORAGE_KEY(PROJECT_ID)]: "conv-1",
    };
    mockLocalStorage(store);

    mockUseConversationMessages.mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof useConversationMessages>);

    const { result } = renderHook(() => usePublishChat(PROJECT_ID), {
      wrapper: createWrapper(),
    });

    const ws = MockWebSocket.instances[0];

    result.current.sendMessage("   ");

    expect(ws.send).not.toHaveBeenCalled();
  });

  // Edge case: WebSocket error event resets streaming state
  it("resets streaming state on WebSocket error message", async () => {
    const store: Record<string, string> = {
      [PUBLISH_CHAT_STORAGE_KEY(PROJECT_ID)]: "conv-1",
    };
    mockLocalStorage(store);

    mockUseConversationMessages.mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof useConversationMessages>);

    const { result } = renderHook(() => usePublishChat(PROJECT_ID), {
      wrapper: createWrapper(),
    });

    const ws = MockWebSocket.instances[0];

    act(() => {
      result.current.sendMessage("trigger stream");
    });
    expect(result.current.isStreaming).toBe(true);

    act(() => {
      ws.onmessage?.({
        data: JSON.stringify({ type: "error", content: "something broke" }),
      });
    });
    await waitFor(() => expect(result.current.isStreaming).toBe(false));
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

    renderHook(() => usePublishChat(PROJECT_ID), {
      wrapper: createWrapper(),
    });

    // Wait a tick to ensure the layout effect has run
    await new Promise((resolve) => setTimeout(resolve, 10));
    expect(mutateAsync).not.toHaveBeenCalled();
  });

  // Mutation-killing: sendMessage trims whitespace and appends to messages
  it("trims whitespace from outgoing messages and appends them", () => {
    const store: Record<string, string> = {
      [PUBLISH_CHAT_STORAGE_KEY(PROJECT_ID)]: "conv-1",
    };
    mockLocalStorage(store);

    mockUseConversationMessages.mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof useConversationMessages>);

    const { result } = renderHook(() => usePublishChat(PROJECT_ID), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.sendMessage("  hello world  ");
    });

    // If content.trim() were mutated to content, the payload would include
    // leading/trailing spaces and the assertion below would fail.
    const ws = MockWebSocket.instances[0];
    expect(ws.send).toHaveBeenCalledWith(
      JSON.stringify({
        content: `(carousel project_id=${PROJECT_ID}) hello world`,
      }),
    );

    // If [...prev, userMsg] were mutated to [], messages would be empty.
    expect(result.current.messages).toHaveLength(1);
    expect(result.current.messages[0]?.content).toBe("hello world");
  });

  // Mutation-killing: COMPLETE message stops streaming
  it("stops streaming when a complete message arrives", async () => {
    const store: Record<string, string> = {
      [PUBLISH_CHAT_STORAGE_KEY(PROJECT_ID)]: "conv-1",
    };
    mockLocalStorage(store);

    mockUseConversationMessages.mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof useConversationMessages>);

    const { result } = renderHook(() => usePublishChat(PROJECT_ID), {
      wrapper: createWrapper(),
    });

    const ws = MockWebSocket.instances[0];

    act(() => {
      result.current.sendMessage("go");
    });
    expect(result.current.isStreaming).toBe(true);

    act(() => {
      ws.onmessage?.({
        data: JSON.stringify({ type: "complete" }),
      });
    });
    await waitFor(() => expect(result.current.isStreaming).toBe(false));
  });

  it("starts a fresh assistant message after complete resets stream state", async () => {
    mockLocalStorage({
      [PUBLISH_CHAT_STORAGE_KEY(PROJECT_ID)]: "conv-1",
    });

    const { result } = renderHook(() => usePublishChat(PROJECT_ID), {
      wrapper: createWrapper(),
    });

    const ws = MockWebSocket.instances[0];
    act(() => {
      ws.onmessage?.({
        data: JSON.stringify({ type: "token", content: "old" }),
      });
      ws.onmessage?.({
        data: JSON.stringify({ type: "complete" }),
      });
      ws.onmessage?.({
        data: JSON.stringify({ type: "token", content: "new" }),
      });
    });

    await waitFor(() => expect(result.current.messages).toHaveLength(2));
    expect(result.current.messages.map((message) => message.content)).toEqual([
      "old",
      "new",
    ]);
  });

  it("starts a fresh assistant message after error resets stream state", async () => {
    mockLocalStorage({
      [PUBLISH_CHAT_STORAGE_KEY(PROJECT_ID)]: "conv-1",
    });

    const { result } = renderHook(() => usePublishChat(PROJECT_ID), {
      wrapper: createWrapper(),
    });

    const ws = MockWebSocket.instances[0];
    act(() => {
      ws.onmessage?.({
        data: JSON.stringify({ type: "token", content: "old" }),
      });
      ws.onmessage?.({
        data: JSON.stringify({ type: "error", content: "failed" }),
      });
      ws.onmessage?.({
        data: JSON.stringify({ type: "token", content: "new" }),
      });
    });

    await waitFor(() => expect(result.current.messages).toHaveLength(2));
    expect(result.current.messages.map((message) => message.content)).toEqual([
      "old",
      "new",
    ]);
  });

  // Mutation-killing: onopen clears optimistic messages
  it("clears optimistic messages when the WebSocket opens", async () => {
    const store: Record<string, string> = {
      [PUBLISH_CHAT_STORAGE_KEY(PROJECT_ID)]: "conv-1",
    };
    mockLocalStorage(store);

    mockUseConversationMessages.mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof useConversationMessages>);

    const { result } = renderHook(() => usePublishChat(PROJECT_ID), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.sendMessage("msg");
    });
    expect(result.current.messages).toHaveLength(1);

    const ws = MockWebSocket.instances[0];
    act(() => {
      ws.onopen?.();
    });
    await waitFor(() => expect(result.current.messages).toHaveLength(0));
    expect(result.current.isStreaming).toBe(false);
  });

  // Mutation-killing: non-refine_carousel_copy tool results do not invalidate
  it("does not invalidate carousel query for unrelated tool results", () => {
    const invalidateQueries = vi.fn();
    mockUseQueryClient.mockReturnValue({
      invalidateQueries,
    } as unknown as ReturnType<typeof useQueryClient>);

    const store: Record<string, string> = {
      [PUBLISH_CHAT_STORAGE_KEY(PROJECT_ID)]: "conv-1",
    };
    mockLocalStorage(store);

    mockUseConversationMessages.mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof useConversationMessages>);

    renderHook(() => usePublishChat(PROJECT_ID), {
      wrapper: createWrapper(),
    });

    const ws = MockWebSocket.instances[0];
    act(() => {
      ws.onmessage?.({
        data: JSON.stringify({
          type: "tool_result",
          tool: "some_other_tool",
        }),
      });
    });

    expect(invalidateQueries).not.toHaveBeenCalled();
  });
});
