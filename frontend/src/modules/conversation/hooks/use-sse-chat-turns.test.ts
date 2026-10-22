/**
 * Gherkin: tests/features/chat-stream-state.feature
 *
 * Pending, failed and overlapping turns of useSseChat, driven through the
 * controllable fake stream in use-sse-chat.test-utils.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { act } from "@testing-library/react";

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

    // Scenario: A double send while the conversation is being created sends one message
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

    // Scenario: The message shows as pending while the conversation is created
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

    // Scenario: A failed send keeps the bubble and gives the text back
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

    // Scenario: A failed send keeps the bubble and gives the text back
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

    // Scenario: Resending after a failure replaces the failed bubble
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

  // Scenario: A double send while the conversation is being created sends one message
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

  // Scenario: Tokens that arrive in one batch render once, in order
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

  // Scenario: A double send while the conversation is being created sends one message
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
});
