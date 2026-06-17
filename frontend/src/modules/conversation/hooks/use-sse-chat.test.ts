/**
 * Gherkin: tests/features/conversation-sse-chat.feature (AE-0155)
 *
 * Race/lifecycle-focused tests for useSseChat using a CONTROLLABLE fake SSE
 * stream (events are driven by the test, not auto-fired) and a REAL QueryClient
 * — so assertions are on observable state, not internal call counts of mocked
 * behavior. Mocks are limited to the network/history seams.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createElement, type ReactNode } from "react";

import type { Message } from "@/schemas/chat";

vi.mock("@/modules/conversation/hooks/use-chat", () => ({
  useConversationMessages: vi.fn(),
}));

vi.mock("@/lib/sse-client", () => ({
  streamSseEvents: vi.fn(),
  SSE_EVENT_TYPE: {
    TOKEN: "token",
    COMPLETE: "complete",
    ERROR: "error",
    SOURCES: "sources",
    TOOL_RESULT: "tool_result",
  },
}));

import { useConversationMessages } from "@/modules/conversation/hooks/use-chat";
import { streamSseEvents } from "@/lib/sse-client";
import { useSseChat } from "./use-sse-chat";

const mockUseConversationMessages = vi.mocked(useConversationMessages);
const mockStream = vi.mocked(streamSseEvents);

const CONV_ID = "conv-1";

type SseEventName = "token" | "complete" | "error" | "sources" | "tool_result";

/** A controllable fake stream: captures each call's callbacks for the test to drive. */
function controllableStream() {
  const calls: Array<{
    opts: Parameters<typeof streamSseEvents>[0];
    resolve: () => void;
  }> = [];
  mockStream.mockImplementation((opts) => {
    return new Promise<void>((resolve) => {
      calls.push({ opts, resolve });
    });
  });
  return {
    get count() {
      return calls.length;
    },
    last: () => calls[calls.length - 1],
    emit(
      event: SseEventName,
      data: Record<string, unknown>,
      i = calls.length - 1,
    ) {
      act(() => calls[i].opts.onEvent({ event, data }));
    },
    complete(i = calls.length - 1) {
      act(() => {
        calls[i].opts.onComplete?.();
        calls[i].resolve();
      });
    },
    fail(message: string, i = calls.length - 1) {
      act(() => calls[i].opts.onError?.(new Error(message)));
    },
  };
}

function setHistory(messages: Message[]) {
  mockUseConversationMessages.mockReturnValue({
    data: messages,
  } as ReturnType<typeof useConversationMessages>);
}

function wrapperWithClient() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");
  const Wrapper = ({ children }: { children: ReactNode }) =>
    createElement(QueryClientProvider, { client: queryClient }, children);
  return { Wrapper, invalidateSpy };
}

function renderChat(options: Parameters<typeof useSseChat>[0] = {}) {
  const { Wrapper, invalidateSpy } = wrapperWithClient();
  const view = renderHook(() => useSseChat(options), { wrapper: Wrapper });
  return { ...view, invalidateSpy };
}

beforeEach(() => {
  vi.clearAllMocks();
  setHistory([]);
});

describe("useSseChat", () => {
  it("accumulates tokens then invalidates history on COMPLETE", async () => {
    const stream = controllableStream();
    const { result, invalidateSpy } = renderChat({ conversationId: CONV_ID });

    await act(async () => {
      void result.current.sendMessage("hello");
    });
    expect(stream.count).toBe(1);
    expect(result.current.isStreaming).toBe(true);

    stream.emit("token", { content: "Hel" });
    stream.emit("token", { content: "lo" });
    const assistant = result.current.messages.at(-1);
    expect(assistant?.role).toBe("assistant");
    expect(assistant?.content).toBe("Hello");

    stream.complete();
    await waitFor(() => expect(result.current.isStreaming).toBe(false));
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ["messages", CONV_ID],
    });
  });

  it("does not invalidate history and keeps optimistic messages when enableHistory is false", async () => {
    const stream = controllableStream();
    const { result, invalidateSpy } = renderChat({
      conversationId: CONV_ID,
      enableHistory: false,
    });

    await act(async () => void result.current.sendMessage("hi"));
    stream.emit("token", { content: "yo" });
    stream.complete();

    await waitFor(() => expect(result.current.isStreaming).toBe(false));
    expect(invalidateSpy).not.toHaveBeenCalled();
    // optimistic user + assistant remain (no history reconciliation)
    expect(result.current.messages.map((m) => m.content)).toEqual(["hi", "yo"]);
  });

  it("surfaces an error and stops streaming on ERROR event", async () => {
    const stream = controllableStream();
    const { result } = renderChat({ conversationId: CONV_ID });

    await act(async () => void result.current.sendMessage("hi"));
    stream.emit("error", { content: "model exploded" });

    expect(result.current.error).toBe("model exploded");
    expect(result.current.isStreaming).toBe(false);
  });

  it("attaches sources from a SOURCES event to the assistant message", async () => {
    const stream = controllableStream();
    const { result } = renderChat({ conversationId: CONV_ID });

    await act(async () => void result.current.sendMessage("hi"));
    stream.emit("token", { content: "answer" });
    stream.emit("sources", { content: [{ id: "s1" }] });

    expect(result.current.messages.at(-1)?.sources).toEqual([{ id: "s1" }]);
  });

  it("dedupes optimistic messages against arriving history (role+content)", async () => {
    controllableStream();
    const { result, rerender } = renderChat({ conversationId: CONV_ID });

    await act(async () => void result.current.sendMessage("dup"));
    expect(
      result.current.messages.filter((m) => m.content === "dup"),
    ).toHaveLength(1);

    // History arrives mid-stream already containing the same user message.
    setHistory([
      { id: "h1", role: "user", content: "dup", sources: [], created_at: "t" },
    ]);
    rerender();

    expect(
      result.current.messages.filter((m) => m.content === "dup"),
    ).toHaveLength(1);
  });

  describe("send guards", () => {
    it("ignores empty content", async () => {
      const stream = controllableStream();
      const { result } = renderChat({ conversationId: CONV_ID });
      await act(async () => void result.current.sendMessage("   "));
      expect(stream.count).toBe(0);
    });

    it("ignores send with no conversation id", async () => {
      const stream = controllableStream();
      const { result } = renderChat({ conversationId: null });
      await act(async () => void result.current.sendMessage("hi"));
      expect(stream.count).toBe(0);
    });

    it("ignores a concurrent send while already streaming", async () => {
      const stream = controllableStream();
      const { result } = renderChat({ conversationId: CONV_ID });
      await act(async () => void result.current.sendMessage("first"));
      expect(stream.count).toBe(1);
      await act(async () => void result.current.sendMessage("second"));
      expect(stream.count).toBe(1); // guarded by isStreaming
    });
  });

  it("finalizes exactly once when COMPLETE and onComplete both fire (idempotent)", async () => {
    const stream = controllableStream();
    const { result, invalidateSpy } = renderChat({ conversationId: CONV_ID });

    await act(async () => void result.current.sendMessage("hi"));
    // COMPLETE event fires finalize; resolving the promise fires onComplete -> finalize again.
    stream.emit("complete", {});
    stream.complete();

    await waitFor(() => expect(result.current.isStreaming).toBe(false));
    expect(invalidateSpy).toHaveBeenCalledTimes(1);
  });

  it("startNewChat aborts the in-flight stream and resets state", async () => {
    const stream = controllableStream();
    const { result } = renderChat({ conversationId: CONV_ID });

    await act(async () => void result.current.sendMessage("hi"));
    const signal = stream.last().opts.signal as AbortSignal;
    expect(signal.aborted).toBe(false);
    expect(result.current.isStreaming).toBe(true);

    act(() => result.current.startNewChat());

    expect(signal.aborted).toBe(true);
    expect(result.current.isStreaming).toBe(false);
    expect(result.current.messages).toHaveLength(0);
  });

  it("aborts the in-flight stream on unmount", async () => {
    const stream = controllableStream();
    const { result, unmount } = renderChat({ conversationId: CONV_ID });

    await act(async () => void result.current.sendMessage("hi"));
    const signal = stream.last().opts.signal as AbortSignal;
    expect(signal.aborted).toBe(false);

    unmount();
    expect(signal.aborted).toBe(true);
  });
});
