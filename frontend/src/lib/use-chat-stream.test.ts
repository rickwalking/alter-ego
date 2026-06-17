/**
 * AE-0150: shared SSE chat streaming hook used by useSseChat and usePublishChat.
 * Verifies the user-turn start, token folding, ref reset, and unmount abort.
 */
import { act, renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { useChatStream } from "./use-chat-stream";

describe("useChatStream", () => {
  it("startUserTurn appends an optimistic user message and starts streaming", () => {
    const { result } = renderHook(() => useChatStream("user-", "stream-"));

    let signal: AbortSignal | undefined;
    act(() => {
      signal = result.current.startUserTurn("hello");
    });

    expect(result.current.isStreaming).toBe(true);
    expect(result.current.optimisticMessages).toHaveLength(1);
    expect(result.current.optimisticMessages[0]).toMatchObject({
      role: "user",
      content: "hello",
    });
    expect(result.current.optimisticMessages[0].id.startsWith("user-")).toBe(
      true,
    );
    expect(signal?.aborted).toBe(false);
  });

  it("appendToken creates then extends the streaming assistant message", () => {
    const { result } = renderHook(() => useChatStream("user-", "stream-"));

    act(() => {
      result.current.startUserTurn("hi");
    });
    act(() => {
      result.current.appendToken("Hel");
    });
    act(() => {
      result.current.appendToken("lo");
    });

    const messages = result.current.optimisticMessages;
    const assistant = messages[messages.length - 1];
    expect(assistant.role).toBe("assistant");
    expect(assistant.content).toBe("Hello");
    expect(assistant.id.startsWith("stream-")).toBe(true);
  });

  it("startUserTurn aborts the previous in-flight stream", () => {
    const { result } = renderHook(() => useChatStream("user-", "stream-"));

    let firstSignal: AbortSignal | undefined;
    act(() => {
      firstSignal = result.current.startUserTurn("first");
    });
    act(() => {
      result.current.startUserTurn("second");
    });

    expect(firstSignal?.aborted).toBe(true);
  });

  it("aborts the in-flight stream on unmount", () => {
    const { result, unmount } = renderHook(() =>
      useChatStream("user-", "stream-"),
    );

    let signal: AbortSignal | undefined;
    act(() => {
      signal = result.current.startUserTurn("hi");
    });
    expect(signal?.aborted).toBe(false);

    unmount();
    expect(signal?.aborted).toBe(true);
  });
});
