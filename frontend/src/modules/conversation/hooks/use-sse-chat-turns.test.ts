/**
 * Gherkin: tests/features/chat-stream-state.feature
 *
 * Pending, failed and overlapping turns of useSseChat, driven through the
 * controllable fake stream in use-sse-chat.test-utils.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { act } from "@testing-library/react";

import { SseHttpError } from "@/lib/sse-http-error";

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

describe("useSseChat turns", () => {
  describe("pending and failed turns", () => {
    function deferred() {
      let resolve: (id: string) => void = () => undefined;
      let reject: (error: Error) => void = () => undefined;
      const promise = new Promise<string>((res, rej) => {
        resolve = res;
        reject = rej;
      });
      return { promise, resolve, reject };
    }

    /** Scenario: A double send while the conversation is being created sends one message */
    it("creates one conversation and streams once on a double send", async () => {
      const stream = controllableStream();
      const creation = deferred();
      const create = vi.fn(() => creation.promise);
      const { result } = renderChat({ conversationId: null });

      let first: Promise<string> = Promise.resolve("");
      let second: Promise<string> = Promise.resolve("");
      act(() => {
        first = result.current.sendMessage("2+2?", create);
        second = result.current.sendMessage("2+2?", create);
      });
      await act(async () => {
        creation.resolve(CONV_ID);
        await second;
      });

      expect(await second).toBe("ignored");
      expect(create).toHaveBeenCalledOnce();
      expect(stream.count).toBe(1);
      expect(
        result.current.messages.filter((m) => m.role === "user"),
      ).toHaveLength(1);
      stream.complete();
      expect(await first).toBe("sent");
    });

    /** Scenario: The message shows as pending while the conversation is created */
    it("shows the user bubble and streaming state before the conversation exists", () => {
      const stream = controllableStream();
      const creation = deferred();
      const { result } = renderChat({ conversationId: null });

      act(() => {
        void result.current.sendMessage("slow network", () => creation.promise);
      });

      expect(stream.count).toBe(0);
      expect(result.current.isStreaming).toBe(true);
      expect(result.current.messages.map((m) => m.content)).toEqual([
        "slow network",
      ]);
    });

    /** Scenario: A failed send keeps the bubble and gives the text back */
    it("keeps the bubble and reports failure when creating the conversation fails", async () => {
      controllableStream();
      const { result } = renderChat({ conversationId: null });

      let outcome = "";
      await act(async () => {
        outcome = await result.current.sendMessage("offline", () =>
          Promise.reject(new TypeError("Failed to fetch")),
        );
      });

      expect(outcome).toBe("failed");
      expect(result.current.error).toBe("offline");
      expect(result.current.isStreaming).toBe(false);
      expect(result.current.messages.map((m) => m.content)).toEqual([
        "offline",
      ]);
    });

    /** Scenario: A failed send keeps the bubble and gives the text back */
    it("reports failure when the stream errors", async () => {
      const stream = controllableStream();
      const { result } = renderChat({ conversationId: CONV_ID });

      let pending: Promise<string> = Promise.resolve("");
      await act(async () => {
        pending = result.current.sendMessage("too long");
        await Promise.resolve();
      });
      stream.fail("HTTP 422");
      stream.complete();

      expect(await pending).toBe("failed");
      expect(result.current.messages.map((m) => m.content)).toEqual([
        "too long",
      ]);
    });

    /** Scenario: Resending after a failure replaces the failed bubble */
    it("replaces the unanswered bubble when the user sends again", async () => {
      const stream = controllableStream();
      const { result } = renderChat({
        conversationId: CONV_ID,
        enableHistory: false,
      });

      const send = async () => {
        await act(async () => {
          void result.current.sendMessage("retry me");
          await Promise.resolve();
        });
      };
      await send();
      stream.emit("error", { content: "boom" });
      await act(async () => {
        stream.last()!.resolve();
        await Promise.resolve();
      });
      await send();
      stream.emit("token", { content: "ok" });

      expect(result.current.messages.map((m) => m.content)).toEqual([
        "retry me",
        "ok",
      ]);
    });

    it("ignores a creation that resolves after the chat was reset", async () => {
      const stream = controllableStream();
      const creation = deferred();
      const { result } = renderChat({ conversationId: null });

      let pending: Promise<string> = Promise.resolve("");
      act(() => {
        pending = result.current.sendMessage("hi", () => creation.promise);
      });
      act(() => result.current.startNewChat());
      await act(async () => {
        creation.resolve(CONV_ID);
        await pending;
      });

      expect(await pending).toBe("ignored");
      expect(stream.count).toBe(0);
    });
  });

  /** Scenario: A double send while the conversation is being created sends one message */
  it("hands the creator the turn's signal, aborted by New chat", async () => {
    controllableStream();
    const create = vi.fn(
      (_signal: AbortSignal) => new Promise<string>(() => undefined),
    );
    const { result } = renderChat({ conversationId: null });

    act(() => {
      void result.current.sendMessage("hi", create);
    });
    await act(async () => {
      await Promise.resolve();
    });
    const signal = create.mock.calls[0]![0];
    expect(signal.aborted).toBe(false);
    act(() => result.current.startNewChat());
    expect(signal.aborted).toBe(true);
  });

  /** Scenario: Tokens that arrive in one batch render once, in order */
  it("keeps a newer turn's bubble when the previous turn's refetch lands", async () => {
    const stream = controllableStream();
    const { result, invalidateSpy } = renderChat({ conversationId: CONV_ID });
    let landRefetch: () => void = () => undefined;
    invalidateSpy.mockReturnValueOnce(
      new Promise<void>((resolve) => {
        landRefetch = resolve;
      }),
    );

    await act(async () => {
      void result.current.sendMessage("first");
      await Promise.resolve();
    });
    stream.emit("token", { content: "one" });
    stream.complete();
    await act(async () => {
      await Promise.resolve();
    });
    await act(async () => {
      void result.current.sendMessage("second");
      await Promise.resolve();
    });
    await act(async () => {
      landRefetch();
      await Promise.resolve();
    });

    expect(result.current.messages.map((m) => m.content)).toContain("second");
  });

  /** Scenario: A double send while the conversation is being created sends one message */
  it("reports busy synchronously while a turn is in flight", async () => {
    const stream = controllableStream();
    const { result } = renderChat({ conversationId: CONV_ID });
    expect(result.current.isBusy()).toBe(false);

    await act(async () => {
      void result.current.sendMessage("hi");
      await Promise.resolve();
    });
    expect(result.current.isBusy()).toBe(true);

    stream.complete();
    await act(async () => {
      await Promise.resolve();
    });
    expect(result.current.isBusy()).toBe(false);
  });

  /** Scenario: Retry is offered only when nothing was saved yet */
  it("ignores a conversation creation that fails after New chat", async () => {
    controllableStream();
    let rejectCreation: ((error: Error) => void) | undefined;
    const creation = new Promise<string>((_resolve, reject) => {
      rejectCreation = reject;
    });
    const { result } = renderChat({ conversationId: null });

    let outcome: Promise<string> = Promise.resolve("");
    act(() => {
      outcome = result.current.sendMessage("hi", () => creation);
    });
    act(() => result.current.startNewChat());
    await act(async () => {
      rejectCreation?.(new TypeError("Failed to fetch"));
      await outcome;
    });

    expect(await outcome).toBe("ignored");
    expect(result.current.error).toBeNull();
  });

  /** Scenario: Retry is offered only when nothing was saved yet */
  it("allows a retry only for a failure before the stream opened", async () => {
    const stream = controllableStream();
    const { result } = renderChat({ conversationId: CONV_ID });

    await act(async () => {
      void result.current.sendMessage("before");
      await Promise.resolve();
    });
    act(() => stream.last()!.opts.onError?.(new SseHttpError(503)));
    expect(result.current.canRetry).toBe(true);
    await act(async () => {
      stream.last()!.resolve();
      await Promise.resolve();
    });

    await act(async () => {
      void result.current.sendMessage("after");
      await Promise.resolve();
    });
    act(() => {
      stream.last()!.opts.onOpen?.();
      stream.last()!.opts.onError?.(new TypeError("network error"));
    });
    expect(result.current.error).toBe("generic");
    expect(result.current.canRetry).toBe(false);
  });

  /** Scenario: A reply that was still streaming appears after a refresh */
  it("reports a reply the server is still writing after a refresh", () => {
    setHistory([
      {
        id: "m1",
        role: "user",
        content: "QA test",
        sources: [],
        created_at: new Date().toISOString(),
      },
    ]);
    const { result } = renderChat({ conversationId: CONV_ID });
    expect(result.current.awaitingReply).toBe(true);
    expect(result.current.isStreaming).toBe(false);
  });

  /** Scenario: Polling stops when nothing is awaited */
  it("does not wait without history", () => {
    const { result } = renderChat({ conversationId: CONV_ID });
    expect(result.current.awaitingReply).toBe(false);
  });

  /** Scenario: A streaming reply can be stopped */
  it("stops a streaming reply and keeps the text that arrived", async () => {
    const stream = controllableStream();
    const { result } = renderChat({
      conversationId: CONV_ID,
      enableHistory: false,
    });
    await act(async () => {
      void result.current.sendMessage("tell me a long story");
      await Promise.resolve();
    });
    stream.emit("token", { content: "Once upon" });

    act(() => result.current.stopStreaming());

    expect(stream.last()!.opts.signal!.aborted).toBe(true);
    expect(result.current.isStreaming).toBe(false);
    expect(result.current.messages.at(-1)?.content).toBe("Once upon");
  });

  /** Scenario: Stopping re-reads the history so the saved reply shows */
  it("re-reads the history and the list after a stop when history is on", async () => {
    const stream = controllableStream();
    const { result, invalidateSpy } = renderChat({ conversationId: CONV_ID });
    await act(async () => {
      void result.current.sendMessage("story");
      await Promise.resolve();
    });

    act(() => result.current.stopStreaming());

    expect(stream.last()!.opts.signal!.aborted).toBe(true);
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["messages"] });
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ["conversations"],
    });
  });

  /** Scenario: Stopping re-reads the history so the saved reply shows */
  it("re-reads nothing after a stop on the public chat", async () => {
    controllableStream();
    const { result, invalidateSpy } = renderChat({
      conversationId: CONV_ID,
      enableHistory: false,
    });
    await act(async () => {
      void result.current.sendMessage("story");
      await Promise.resolve();
    });

    act(() => result.current.stopStreaming());

    expect(invalidateSpy).not.toHaveBeenCalled();
  });

  /** Scenario: A failed reply is re-read from the history */
  it("re-reads the history after a failed reply when history is on", async () => {
    const stream = controllableStream();
    const { result, invalidateSpy } = renderChat({ conversationId: CONV_ID });
    let outcome: Promise<string> = Promise.resolve("");
    await act(async () => {
      outcome = result.current.sendMessage("story");
      await Promise.resolve();
    });

    await act(async () => {
      stream.last()!.opts.onOpen?.();
      stream.last()!.opts.onEvent({ event: "error", data: {} });
      stream.last()!.resolve();
      await outcome;
    });

    expect(await outcome).toBe("failed");
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["messages"] });
  });

  /** Scenario: After a stop the next message is sent */
  it("does not bring the stopped part back with the next message", async () => {
    const stream = controllableStream();
    const { result, rerender } = renderChat({ conversationId: CONV_ID });
    await act(async () => {
      void result.current.sendMessage("story");
      await Promise.resolve();
    });
    stream.emit("token", { content: "Once upon" });
    act(() => result.current.stopStreaming());
    await act(async () => {
      stream.last()!.resolve();
      await Promise.resolve();
    });
    setHistory([
      {
        id: "u",
        role: "user",
        content: "story",
        sources: [],
        created_at: new Date().toISOString(),
      },
      {
        id: "a",
        role: "assistant",
        content: "Once upon a time.",
        sources: [],
        created_at: new Date().toISOString(),
      },
    ]);
    rerender();

    await act(async () => {
      void result.current.sendMessage("next");
      await Promise.resolve();
    });

    expect(result.current.messages.map((m) => m.content)).toEqual([
      "story",
      "Once upon a time.",
      "next",
    ]);
  });

  /** Scenario: After a stop the next message is sent */
  it("sends the next message after a stop", async () => {
    const stream = controllableStream();
    const { result } = renderChat({
      conversationId: CONV_ID,
      enableHistory: false,
    });
    await act(async () => {
      void result.current.sendMessage("first");
      await Promise.resolve();
    });
    act(() => result.current.stopStreaming());
    await act(async () => {
      stream.last()!.resolve();
      await Promise.resolve();
    });

    await act(async () => {
      void result.current.sendMessage("second");
      await Promise.resolve();
    });

    expect(stream.count).toBe(2);
    expect(result.current.isStreaming).toBe(true);
  });

  /** Scenario: A streaming reply can be stopped */
  it("shows the saved reply once, not next to the stopped part", async () => {
    const stream = controllableStream();
    const { result, rerender } = renderChat({ conversationId: CONV_ID });
    await act(async () => {
      void result.current.sendMessage("story");
      await Promise.resolve();
    });
    stream.emit("token", { content: "Once upon" });
    act(() => result.current.stopStreaming());

    setHistory([
      {
        id: "u",
        role: "user",
        content: "story",
        sources: [],
        created_at: new Date().toISOString(),
      },
      {
        id: "a",
        role: "assistant",
        content: "Once upon a time.",
        sources: [],
        created_at: new Date().toISOString(),
      },
    ]);
    rerender();

    expect(result.current.messages.map((m) => m.content)).toEqual([
      "story",
      "Once upon a time.",
    ]);
  });
});
