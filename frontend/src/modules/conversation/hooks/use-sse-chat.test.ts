/**
 * Gherkin: tests/features/conversation-sse-chat.feature,
 * tests/features/chat-stream-state.feature
 *
 * Race/lifecycle-focused tests for useSseChat using a CONTROLLABLE fake SSE
 * stream (events are driven by the test, not auto-fired) and a REAL QueryClient
 * — so assertions are on observable state, not internal call counts of mocked
 * behavior. Mocks are limited to the network/history seams.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { act, waitFor } from "@testing-library/react";

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

import {
  CONV_ID,
  controllableStream,
  renderChat,
  setHistory,
} from "./use-sse-chat.test-utils";

beforeEach(() => {
  vi.clearAllMocks();
  setHistory([]);
});

describe("useSseChat", () => {
  it("accumulates tokens then invalidates history on COMPLETE", async () => {
    const stream = controllableStream();
    const { result, invalidateSpy } = renderChat({ conversationId: CONV_ID });

    await act(() => {
      void result.current.sendMessage("hello");
      return Promise.resolve();
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

    await act(() => Promise.resolve(void result.current.sendMessage("hi")));
    stream.emit("token", { content: "yo" });
    stream.complete();

    await waitFor(() => expect(result.current.isStreaming).toBe(false));
    expect(invalidateSpy).not.toHaveBeenCalled();
    expect(result.current.messages.map((m) => m.content)).toEqual(["hi", "yo"]);
  });

  it("surfaces an error and stops streaming on ERROR event", async () => {
    const stream = controllableStream();
    const { result } = renderChat({ conversationId: CONV_ID });

    await act(() => Promise.resolve(void result.current.sendMessage("hi")));
    stream.emit("error", { content: "model exploded" });

    expect(result.current.error).toBe("generic");
    expect(result.current.isStreaming).toBe(false);
  });

  it("attaches sources from a SOURCES event to the assistant message", async () => {
    const stream = controllableStream();
    const { result } = renderChat({ conversationId: CONV_ID });

    await act(() => Promise.resolve(void result.current.sendMessage("hi")));
    stream.emit("token", { content: "answer" });
    stream.emit("sources", { content: [{ id: "s1" }] });

    expect(result.current.messages.at(-1)?.sources).toEqual([{ id: "s1" }]);
  });

  it("dedupes optimistic messages against arriving history (role+content)", async () => {
    controllableStream();
    const { result, rerender } = renderChat({ conversationId: CONV_ID });

    await act(() => Promise.resolve(void result.current.sendMessage("dup")));
    expect(
      result.current.messages.filter((m) => m.content === "dup"),
    ).toHaveLength(1);

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
      await act(() => Promise.resolve(void result.current.sendMessage("   ")));
      expect(stream.count).toBe(0);
    });

    it("ignores send with no conversation id", async () => {
      const stream = controllableStream();
      const { result } = renderChat({ conversationId: null });
      await act(() => Promise.resolve(void result.current.sendMessage("hi")));
      expect(stream.count).toBe(0);
    });

    it("ignores a concurrent send while already streaming", async () => {
      const stream = controllableStream();
      const { result } = renderChat({ conversationId: CONV_ID });
      await act(() =>
        Promise.resolve(void result.current.sendMessage("first")),
      );
      expect(stream.count).toBe(1);
      await act(() =>
        Promise.resolve(void result.current.sendMessage("second")),
      );
      expect(stream.count).toBe(1);
    });
  });

  it("finalizes exactly once when COMPLETE and onComplete both fire (idempotent)", async () => {
    const stream = controllableStream();
    const { result, invalidateSpy } = renderChat({ conversationId: CONV_ID });

    await act(() => Promise.resolve(void result.current.sendMessage("hi")));
    stream.emit("complete", {});
    stream.complete();

    await waitFor(() => expect(result.current.isStreaming).toBe(false));
    expect(invalidateSpy).toHaveBeenCalledTimes(1);
  });

  it("startNewChat aborts the in-flight stream and resets state", async () => {
    const stream = controllableStream();
    const { result } = renderChat({ conversationId: CONV_ID });

    await act(() => Promise.resolve(void result.current.sendMessage("hi")));
    const signal = stream.last()!.opts.signal!;
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

    await act(() => Promise.resolve(void result.current.sendMessage("hi")));
    const signal = stream.last()!.opts.signal!;
    expect(signal.aborted).toBe(false);

    unmount();
    expect(signal.aborted).toBe(true);
  });
});
