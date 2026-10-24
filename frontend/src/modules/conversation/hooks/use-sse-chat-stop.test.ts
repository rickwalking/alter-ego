/**
 * Gherkin: tests/features/chat-polish.feature
 *
 * Stop, then what follows it, driven through the controllable fake stream.
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
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

import { CHAT_TURN_IN_FLIGHT_CODE } from "../constants";
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

function saved(role: "user" | "assistant", content: string) {
  return {
    id: `${role}-${content}`,
    role,
    content,
    sources: [],
    created_at: new Date().toISOString(),
  };
}

describe("useSseChat stop", () => {
  /** Scenario: Stop is offered once the reply has started */
  it("offers Stop only once the answer stream has opened", async () => {
    const stream = controllableStream();
    const { result } = renderChat({ conversationId: CONV_ID });
    await act(async () => {
      void result.current.sendMessage("story");
      await Promise.resolve();
    });
    expect(result.current.isStreaming).toBe(true);
    expect(result.current.canStop).toBe(false);

    act(() => stream.last()!.opts.onOpen?.());
    expect(result.current.canStop).toBe(true);

    act(() => result.current.stopStreaming());
    expect(result.current.canStop).toBe(false);
  });

  /** Scenario: After a stop, the chat waits for the saved reply */
  it("keeps the turn open after a stop until its saved reply arrives", async () => {
    const stream = controllableStream();
    const { result, rerender } = renderChat({ conversationId: CONV_ID });
    await act(async () => {
      void result.current.sendMessage("story");
      await Promise.resolve();
    });
    act(() => stream.last()!.opts.onOpen?.());
    stream.emit("token", { content: "Once upon" });
    act(() => result.current.stopStreaming());

    expect(result.current.isStreaming).toBe(false);
    expect(result.current.awaitingReply).toBe(true);

    setHistory([saved("user", "story")]);
    rerender();
    expect(result.current.awaitingReply).toBe(true);

    setHistory([
      saved("user", "story"),
      saved("assistant", "Once upon a time."),
    ]);
    rerender();
    expect(result.current.awaitingReply).toBe(false);
    expect(result.current.messages.map((m) => m.content)).toEqual([
      "story",
      "Once upon a time.",
    ]);
  });

  /** Scenario: After a stop, the chat waits for the saved reply */
  it("keeps a stopped turn on screen when the next message is sent (no history)", async () => {
    const stream = controllableStream();
    const { result } = renderChat({
      conversationId: CONV_ID,
      enableHistory: false,
    });
    await act(async () => {
      void result.current.sendMessage("first");
      await Promise.resolve();
    });
    act(() => stream.last()!.opts.onOpen?.());
    act(() => result.current.stopStreaming());
    await act(async () => {
      stream.last()!.resolve();
      await Promise.resolve();
    });

    await act(async () => {
      void result.current.sendMessage("second");
      await Promise.resolve();
    });

    expect(result.current.messages.map((m) => m.content)).toEqual([
      "first",
      "second",
    ]);
    expect(result.current.awaitingReply).toBe(false);
  });

  /** Scenario: A message sent while the previous reply is still being saved */
  it("says the previous reply is still being finished, and allows a retry", async () => {
    const stream = controllableStream();
    const { result } = renderChat({
      conversationId: CONV_ID,
      enableHistory: false,
    });
    await act(async () => {
      void result.current.sendMessage("too soon");
      await Promise.resolve();
    });
    act(() => stream.last()!.opts.onOpen?.());

    stream.emit("error", {
      content: "A reply to this conversation is still being written.",
      code: CHAT_TURN_IN_FLIGHT_CODE,
    });

    expect(result.current.error).toBe("busy");
    expect(result.current.canRetry).toBe(true);
  });

  /** Scenario: A message sent while the previous reply is still being saved */
  it("keeps any other error event generic and not retryable", async () => {
    const stream = controllableStream();
    const { result } = renderChat({
      conversationId: CONV_ID,
      enableHistory: false,
    });
    await act(async () => {
      void result.current.sendMessage("hi");
      await Promise.resolve();
    });
    act(() => stream.last()!.opts.onOpen?.());

    stream.emit("error", { content: "Sorry" });

    expect(result.current.error).toBe("generic");
    expect(result.current.canRetry).toBe(false);
  });
});
