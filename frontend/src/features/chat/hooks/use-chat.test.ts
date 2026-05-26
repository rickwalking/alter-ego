import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createElement, type ReactNode } from "react";
import {
  MESSAGES_KEY,
  useConversation,
  useConversationMessages,
  useConversations,
  useCreateConversation,
  useDeleteConversation,
  useSendMessage,
} from "./use-chat";
import { API_ENDPOINTS } from "@/constants/api";

vi.mock("@/lib/api-client", () => ({
  apiCall: vi.fn(),
  apiCallNoContent: vi.fn(),
  ApiError: class ApiError extends Error {
    constructor(
      public status: number,
      message: string,
      public code?: string,
    ) {
      super(message);
      this.name = "ApiError";
    }
  },
}));

import { apiCall, apiCallNoContent, ApiError } from "@/lib/api-client";

const mockApiCall = vi.mocked(apiCall);
const mockDelete = vi.mocked(apiCallNoContent);

const MOCK_CONVERSATION = {
  id: "conv-1",
  title: "Existing conversation",
  metadata: { source: "test" },
  created_at: "2026-04-20T00:00:00Z",
  updated_at: "2026-04-20T00:00:00Z",
};

const MOCK_MESSAGE = {
  id: "msg-1",
  role: "user" as const,
  content: "Hello",
  sources: [],
  created_at: "2026-04-20T00:00:00Z",
};

function createQueryClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: Infinity } },
  });
}

function createWrapper(queryClient = createQueryClient()) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return createElement(
      QueryClientProvider,
      { client: queryClient },
      children,
    );
  };
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("useConversations", () => {
  it("fetches conversations and stores them under the conversations query key", async () => {
    mockApiCall.mockResolvedValueOnce({
      items: [MOCK_CONVERSATION],
      total: 1,
      limit: 20,
      offset: 0,
    });
    const queryClient = createQueryClient();
    const { result } = renderHook(() => useConversations(), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockApiCall).toHaveBeenCalledWith(
      API_ENDPOINTS.CONVERSATIONS,
      expect.anything(),
    );
    expect(result.current.data).toEqual([MOCK_CONVERSATION]);
    expect(queryClient.getQueryData(["conversations"])).toEqual([
      MOCK_CONVERSATION,
    ]);
  });
});

describe("useConversation", () => {
  it("fetches one conversation by id", async () => {
    mockApiCall.mockResolvedValueOnce(MOCK_CONVERSATION);
    const queryClient = createQueryClient();
    const { result } = renderHook(() => useConversation("conv-1"), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockApiCall).toHaveBeenCalledWith(
      API_ENDPOINTS.CONVERSATION_BY_ID("conv-1"),
      expect.anything(),
    );
    expect(queryClient.getQueryData(["conversation", "conv-1"])).toEqual(
      MOCK_CONVERSATION,
    );
  });

  it("is disabled without a conversation id", () => {
    const { result } = renderHook(() => useConversation(null), {
      wrapper: createWrapper(),
    });

    expect(result.current.fetchStatus).toBe("idle");
    expect(mockApiCall).not.toHaveBeenCalled();
  });
});

describe("useConversationMessages", () => {
  it("fetches messages by conversation id", async () => {
    mockApiCall.mockResolvedValueOnce({
      items: [MOCK_MESSAGE],
      conversation_id: "conv-1",
    });
    const queryClient = createQueryClient();
    const { result } = renderHook(() => useConversationMessages("conv-1"), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockApiCall).toHaveBeenCalledWith(
      API_ENDPOINTS.CONVERSATION_MESSAGES("conv-1"),
      expect.anything(),
    );
    expect(queryClient.getQueryData([MESSAGES_KEY, "conv-1"])).toEqual([
      MOCK_MESSAGE,
    ]);
  });

  it("is disabled without a conversation id", () => {
    const { result } = renderHook(() => useConversationMessages(null), {
      wrapper: createWrapper(),
    });

    expect(result.current.fetchStatus).toBe("idle");
    expect(mockApiCall).not.toHaveBeenCalled();
  });
});

describe("useCreateConversation", () => {
  it("posts title and metadata then invalidates conversations", async () => {
    mockApiCall.mockResolvedValueOnce(MOCK_CONVERSATION);
    const queryClient = createQueryClient();
    queryClient.setQueryData(
      ["conversations"],
      [
        {
          ...MOCK_CONVERSATION,
          id: "conv-old",
          title: "Old conversation",
        },
      ],
    );
    const invalidateQueries = vi.spyOn(queryClient, "invalidateQueries");
    const { result } = renderHook(() => useCreateConversation(), {
      wrapper: createWrapper(queryClient),
    });

    result.current.mutate({
      title: "New chat",
      metadata: { project_id: "project-1" },
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockApiCall).toHaveBeenCalledWith(
      API_ENDPOINTS.CONVERSATIONS,
      expect.anything(),
      {
        method: "POST",
        body: JSON.stringify({
          title: "New chat",
          metadata: { project_id: "project-1" },
        }),
      },
    );
    expect(invalidateQueries).toHaveBeenCalledWith({
      queryKey: ["conversations"],
    });
    expect(queryClient.getQueryData(["conversation", "conv-1"])).toEqual(
      MOCK_CONVERSATION,
    );
    expect(queryClient.getQueryData(["conversations"])).toEqual([
      MOCK_CONVERSATION,
      {
        ...MOCK_CONVERSATION,
        id: "conv-old",
        title: "Old conversation",
      },
    ]);
  });

  it("deduplicates the created conversation in the cache by id", async () => {
    mockApiCall.mockResolvedValueOnce(MOCK_CONVERSATION);
    const queryClient = createQueryClient();
    queryClient.setQueryData(
      ["conversations"],
      [
        MOCK_CONVERSATION,
        {
          ...MOCK_CONVERSATION,
          id: "conv-old",
          title: "Old conversation",
        },
      ],
    );
    const { result } = renderHook(() => useCreateConversation(), {
      wrapper: createWrapper(queryClient),
    });

    result.current.mutate({
      title: "Duplicate id",
      metadata: { project_id: "project-1" },
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(queryClient.getQueryData(["conversations"])).toEqual([
      MOCK_CONVERSATION,
      {
        ...MOCK_CONVERSATION,
        id: "conv-old",
        title: "Old conversation",
      },
    ]);
  });

  it("logs create errors without updating the cache", async () => {
    const consoleError = vi
      .spyOn(console, "error")
      .mockImplementation(() => {});
    mockApiCall.mockRejectedValueOnce(new Error("create failed"));
    const queryClient = createQueryClient();
    queryClient.setQueryData(["conversations"], [MOCK_CONVERSATION]);
    const { result } = renderHook(() => useCreateConversation(), {
      wrapper: createWrapper(queryClient),
    });

    result.current.mutate({ title: "Broken" });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(consoleError).toHaveBeenCalledWith(
      "Failed to create conversation:",
      expect.any(Error),
    );
    expect(queryClient.getQueryData(["conversations"])).toEqual([
      MOCK_CONVERSATION,
    ]);
    consoleError.mockRestore();
  });
});

describe("useSendMessage", () => {
  it("posts message content and invalidates messages plus conversations", async () => {
    mockApiCall.mockResolvedValueOnce({
      content: "Answer",
      sources: [],
      conversation_id: "conv-1",
    });
    const queryClient = createQueryClient();
    const invalidateQueries = vi.spyOn(queryClient, "invalidateQueries");
    const { result } = renderHook(() => useSendMessage(), {
      wrapper: createWrapper(queryClient),
    });

    result.current.mutate({ conversationId: "conv-1", content: "Hello" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockApiCall).toHaveBeenCalledWith(
      API_ENDPOINTS.CONVERSATION_CHAT("conv-1"),
      expect.anything(),
      {
        method: "POST",
        body: JSON.stringify({ content: "Hello" }),
      },
    );
    expect(invalidateQueries).toHaveBeenCalledWith({
      queryKey: [MESSAGES_KEY, "conv-1"],
    });
    expect(invalidateQueries).toHaveBeenCalledWith({
      queryKey: ["conversations"],
    });
  });

  it("logs send errors without invalidating queries", async () => {
    const consoleError = vi
      .spyOn(console, "error")
      .mockImplementation(() => {});
    mockApiCall.mockRejectedValueOnce(new Error("send failed"));
    const queryClient = createQueryClient();
    const invalidateQueries = vi.spyOn(queryClient, "invalidateQueries");
    const { result } = renderHook(() => useSendMessage(), {
      wrapper: createWrapper(queryClient),
    });

    result.current.mutate({ conversationId: "conv-1", content: "Hello" });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(consoleError).toHaveBeenCalledWith(
      "Failed to send message:",
      expect.any(Error),
    );
    expect(invalidateQueries).not.toHaveBeenCalled();
    consoleError.mockRestore();
  });
});

describe("useDeleteConversation", () => {
  // Scenario: Given a successful DELETE, the mutation resolves.
  it("calls the DELETE endpoint for the given id", async () => {
    mockDelete.mockResolvedValueOnce(undefined);
    const queryClient = createQueryClient();
    queryClient.setQueryData(
      ["conversations"],
      [
        MOCK_CONVERSATION,
        {
          ...MOCK_CONVERSATION,
          id: "conv-2",
          title: "Keep me",
        },
      ],
    );
    queryClient.setQueryData(["conversation", "conv-1"], MOCK_CONVERSATION);
    queryClient.setQueryData([MESSAGES_KEY, "conv-1"], [MOCK_MESSAGE]);
    const invalidateQueries = vi.spyOn(queryClient, "invalidateQueries");
    const removeQueries = vi.spyOn(queryClient, "removeQueries");
    const { result } = renderHook(() => useDeleteConversation(), {
      wrapper: createWrapper(queryClient),
    });

    result.current.mutate("conv-1");

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockDelete).toHaveBeenCalledWith(
      API_ENDPOINTS.CONVERSATION_BY_ID("conv-1"),
      { method: "DELETE" },
    );
    expect(invalidateQueries).toHaveBeenCalledWith({
      queryKey: ["conversations"],
    });
    expect(removeQueries).toHaveBeenCalledWith({
      queryKey: ["conversation", "conv-1"],
    });
    expect(removeQueries).toHaveBeenCalledWith({
      queryKey: [MESSAGES_KEY, "conv-1"],
    });
    expect(queryClient.getQueryData(["conversations"])).toEqual([
      {
        ...MOCK_CONVERSATION,
        id: "conv-2",
        title: "Keep me",
      },
    ]);
  });

  // Scenario: Given a 404, the mutation surfaces an ApiError.
  it("surfaces api errors to the caller", async () => {
    mockDelete.mockRejectedValueOnce(new ApiError(404, "not found"));
    const { result } = renderHook(() => useDeleteConversation(), {
      wrapper: createWrapper(),
    });

    result.current.mutate("conv-1");

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect((result.current.error as ApiError).status).toBe(404);
  });

  it("leaves the conversations cache unchanged when it was never loaded", async () => {
    mockDelete.mockResolvedValueOnce(undefined);
    const queryClient = createQueryClient();
    const removeQueries = vi.spyOn(queryClient, "removeQueries");
    const { result } = renderHook(() => useDeleteConversation(), {
      wrapper: createWrapper(queryClient),
    });

    result.current.mutate("conv-1");

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(queryClient.getQueryData(["conversations"])).toBeUndefined();
    expect(removeQueries).toHaveBeenCalledWith({
      queryKey: ["conversation", "conv-1"],
    });
  });

  it("logs delete errors without mutating the cache", async () => {
    const consoleError = vi
      .spyOn(console, "error")
      .mockImplementation(() => {});
    mockDelete.mockRejectedValueOnce(new ApiError(500, "delete failed"));
    const queryClient = createQueryClient();
    queryClient.setQueryData(["conversations"], [MOCK_CONVERSATION]);
    const { result } = renderHook(() => useDeleteConversation(), {
      wrapper: createWrapper(queryClient),
    });

    result.current.mutate("conv-1");

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(consoleError).toHaveBeenCalledWith(
      "Failed to delete conversation:",
      expect.any(ApiError),
    );
    expect(queryClient.getQueryData(["conversations"])).toEqual([
      MOCK_CONVERSATION,
    ]);
    consoleError.mockRestore();
  });
});
